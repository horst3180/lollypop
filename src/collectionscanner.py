#!/usr/bin/python
# Copyright (c) 2014-2015 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import os
from time import sleep
from gettext import gettext as _
from gi.repository import GLib, GObject
from _thread import start_new_thread

from lollypop.define import Objects, Navigation
from lollypop.utils import format_artist_name


class CollectionScanner(GObject.GObject):
    __gsignals__ = {
        'scan-finished': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'add-finished': (GObject.SignalFlags.RUN_FIRST, None, ())
    }
    _mimes = ["mp3", "ogg", "flac", "m4a", "mp4", "opus"]

    """
        @param progress as Gtk.Progress
    """
    def __init__(self, progress):
        GObject.GObject.__init__(self)

        self._progress = progress
        self._in_thread = False
        self._smooth = False
        self._added = []
         
    """
        Update database
        @param smooth as bool, if smooth, try to scan smoothly
    """
    def update(self, smooth):
        self._smooth = smooth
        paths = Objects.settings.get_value('music-path')
        if not paths:
            if GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_MUSIC):
                paths = [GLib.get_user_special_dir(
                                          GLib.UserDirectory.DIRECTORY_MUSIC)]
            else:
                print("You need to add a music path"
                      " to org.gnome.Lollypop in dconf")
                return

        if not self._in_thread:
            self._progress.show()
            self._in_thread = True
            self._compilations = []
            self._mtimes = Objects.tracks.get_mtimes()
            start_new_thread(self._scan, (paths,))

    """
        Add specified files to collection
        @param files as [Gio.Files]
        @thread safe
    """
    def add(self, files):
        GLib.idle_add(self._progress.show)
        sql = Objects.db.get_cursor()
        tracks = Objects.tracks.get_paths(sql)
        count = len(files)
        i = 0
        GLib.idle_add(self._update_progress, i, count)
        self._added = []
        for f in files:
            path = f.get_path()
            if path not in tracks:
                infos = Objects.player.get_infos(path)
                self._added.append(self._add2db(path, 0, infos, sql))
            i += 1
            GLib.idle_add(self._update_progress, i, count)
        Objects.albums.sanitize(sql)
        sql.commit()
        sql.close()     
        GLib.idle_add(self._progress.hide)     
        GLib.idle_add(self.emit, "add-finished")

    """
        Return files added by last call to CollectionScanner::add
        @return [int]
    """
    def get_added(self):
        return self._added

#######################
# PRIVATE             #
#######################

    """
        Update progress bar status
        @param scanned items as int, total items as int
    """
    def _update_progress(self, current, total):
        self._progress.set_fraction(current/total)

    """
        Notify from main thread when scan finished
    """
    def _finish(self):
        self._in_thread = False
        self._progress.hide()
        self.emit("scan-finished")

    """
        Clean track's compilation if needed
        @param album id as int
    """
    def _clean_compilation(self, album_id, sql=None):
        artists = Objects.albums.get_compilation_artists(album_id, sql)
        # It's not a compilation anymore
        if len(artists) == 1:
            artist_id = artists[0]
            Objects.albums.set_artist_id(album_id, artist_id, sql)
            # Update album path
            tracks = Objects.albums.get_tracks(album_id, None, sql)
            filepath = Objects.tracks.get_path(tracks[0], sql)
            path = os.path.dirname(filepath)
            Objects.albums.set_path(album_id, path, sql)

    """
        Scan music collection for music files
        @param paths as [string], paths to scan
    """
    def _scan(self, paths):
        sql = Objects.db.get_cursor()

        tracks = Objects.tracks.get_paths(sql)
        new_tracks = []
        count = 0
        for path in paths:
            for root, dirs, files in os.walk(path):
                for f in files:
                    lowername = f.lower()
                    supported = False
                    for mime in self._mimes:
                        if lowername.endswith(mime):
                            supported = True
                            break
                    if supported:
                        new_tracks.append(os.path.join(root, f))
                        count += 1

        i = 0
        for filepath in new_tracks:
            GLib.idle_add(self._update_progress, i, count)
            mtime = int(os.path.getmtime(filepath))
            try:
                if filepath not in tracks:
                    infos = Objects.player.get_infos(filepath)
                    self._add2db(filepath, mtime, infos, sql)
                else:
                    # Update tags by removing song and readd it
                    if mtime != self._mtimes[filepath]:
                        infos = Objects.player.get_infos(filepath)
                        track_id = Objects.tracks.get_id_by_path(filepath, sql)
                        album_id = Objects.tracks.get_album_id(track_id, sql)
                        Objects.tracks.remove(filepath, sql)
                        self._clean_compilation(album_id, sql)
                        self._add2db(filepath, mtime, infos, sql)
                    tracks.remove(filepath)

            except Exception as e:
                print(ascii(filepath))
                print("CollectionScanner::_scan(): %s" % e)
            i += 1
            if self._smooth:
                sleep(0.001)

        # Clean deleted files
        if i > 0:
            for filepath in tracks:
                track_id = Objects.tracks.get_id_by_path(filepath, sql)
                album_id = Objects.tracks.get_album_id(track_id, sql)
                Objects.tracks.remove(filepath, sql)
                self._clean_compilation(album_id, sql)

        Objects.tracks.clean(sql)
        Objects.albums.sanitize(sql)
        self._restore_popularities(sql)
        sql.commit()
        sql.close()
        GLib.idle_add(self._finish)

    """
        Add new file to db with informations
        @param filepath as string
        @param file modification time as int
        @param infos as GstPbutils.DiscovererInfo
        @param sql as sqlite cursor
        @return track id as int
    """
    def _add2db(self, filepath, mtime, infos, sql):
        path = os.path.dirname(filepath)

        tags = infos.get_tags()

        (exist, title) = tags.get_string_index('title', 0)
        if not exist:
            title = os.path.basename(filepath)

        (exist, artists) = tags.get_string_index('artist', 0)
        if not exist:
            artists = _("Unknown")

        artists = ""
        size = tags.get_tag_size('artist')
        if size == 0:
            artists = _("Unknown")
        else:
            for i in range(0, size):
                (exist, artist) = tags.get_string_index('artist', i)
                artists += artist
                if i < size-1:
                    artists += ";"

        (exist, performer) = tags.get_string_index('album-artist', 0)
        if not exist:
            performer = None

        (exist, album) = tags.get_string_index('album', 0)
        if not exist:
            album = _("Unknown")

        genres = ""
        size = tags.get_tag_size('genre')
        if size == 0:
            genres = _("Unknown")
        else:
            for i in range(0, size):
                (exist, genre) = tags.get_string_index('genre', i)
                genres += genre
                if i < size-1:
                    genres += ";"

        (exist, discnumber) = tags.get_int_index('disc-number', 0)
        if not exist:
            discnumber = 0

        (exist, tracknumber) = tags.get_int_index('track-number', 0)
        if not exist:
            tracknumber = 0

        (exist, datetime) = tags.get_date_time('datetime')
        if exist:
            year = datetime.get_year()
        else:
            year = None

        length = infos.get_duration()/1000000000

        # Get all artist ids
        artist_ids = []
        for word in artists.split(';'):
            artist = format_artist_name(word)
            # Get artist id, add it if missing
            artist_id = Objects.artists.get_id(artist, sql)
            if artist_id is None:
                Objects.artists.add(artist, sql)
                artist_id = Objects.artists.get_id(artist, sql)
            artist_ids.append(artist_id)

        if performer:
            # Get performer id, add it if missing
            performer_id = Objects.artists.get_id(performer, sql)
            if performer_id is None:
                Objects.artists.add(performer, sql)
                performer_id = Objects.artists.get_id(performer, sql)
        else:
            performer_id = Navigation.COMPILATIONS

        # Get all genre ids
        genre_ids = []
        for genre in genres.split(';'):
            # Get genre id, add genre if missing
            genre_id = Objects.genres.get_id(genre, sql)
            if genre_id is None:
                Objects.genres.add(genre, sql)
                genre_id = Objects.genres.get_id(genre, sql)
            genre_ids.append(genre_id)

        album_id = Objects.albums.get_id(album, performer_id, sql)
        if album_id is None:
            Objects.albums.add(album, performer_id,
                               path, 0, sql)
            album_id = Objects.albums.get_id(album, performer_id, sql)

        for genre_id in genre_ids:
            Objects.albums.add_genre(album_id, genre_id, sql)

        # Now we have our album id, check if path doesn't change
        if Objects.albums.get_path(album_id, sql) != path:
            Objects.albums.set_path(album_id, path, sql)

        # Add track to db
        Objects.tracks.add(title, filepath, length,
                           tracknumber, discnumber,
                           album_id, year, mtime, sql)

        # Update year for album
        year = Objects.albums.get_year_from_tracks(album_id, sql)
        Objects.albums.set_year(album_id, year, sql)

        # Set artists/genres for track
        track_id = Objects.tracks.get_id_by_path(filepath, sql)
        for artist_id in artist_ids:
            Objects.tracks.add_artist(track_id, artist_id, sql)
        for genre_id in genre_ids:
            Objects.tracks.add_genre(track_id, genre_id, sql)
        return track_id

    """
        Restore albums popularties
    """
    def _restore_popularities(self, sql):
        self._popularities = Objects.db.get_popularities()
        result = sql.execute("SELECT albums.name, artists.name, albums.rowid\
                              FROM albums, artists\
                              WHERE artists.rowid == albums.artist_id")
        for row in result:
            string = "%s_%s" % (row[0], row[1])
            if string in self._popularities:
                Objects.albums.set_popularity(row[2],
                                              self._popularities[string], sql)
