#!/usr/bin/python
# Copyright (c) 2014-2015 Cedric Bellegarde <gnumdk@gmail.com>
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
import mutagen

from lollypop.define import Objects, COMPILATIONS
from lollypop.utils import format_artist_name


class CollectionScanner(GObject.GObject):
    __gsignals__ = {
        'scan-finished': (GObject.SIGNAL_RUN_FIRST, None, ()),
    }
    _mimes = ["mp3", "ogg", "flac", "m4a", "mp4", "opus"]

    def __init__(self):
        GObject.GObject.__init__(self)

        self._in_thread = False
        self._progress = None
        self._smooth = False
        self._popularities = Objects.db.get_popularities()

    """
        Update database
        @param progress as Gtk.Progress
        @param smooth as bool, if smooth, try to scan smoothly
    """
    def update(self,  progress, smooth):
        self._smooth = smooth
        paths = Objects.settings.get_value('music-path')
        if not paths:
            if GLib.get_user_special_dir(GLib.USER_DIRECTORY_MUSIC):
                paths = [GLib.get_user_special_dir(GLib.USER_DIRECTORY_MUSIC)]
            else:
                print("You need to add a music path"
                      " to org.gnome.Lollypop in dconf")
                return

        if not self._in_thread:
            self._progress = progress
            progress.show()
            self._in_thread = True
            self._compilations = []
            self._mtimes = Objects.tracks.get_mtimes()
            start_new_thread(self._scan, (paths,))

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
            tracks = Objects.albums.get_tracks(album_id, sql)
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
                    tag = mutagen.File(filepath, easy=True)
                    self._add2db(filepath, mtime, tag, sql)
                else:
                    # Update tags by removing song and readd it
                    if mtime != self._mtimes[filepath]:
                        tag = mutagen.File(filepath, easy=True)
                        track_id = Objects.tracks.get_id_by_path(filepath, sql)
                        album_id = Objects.tracks.get_album_id(track_id, sql)
                        Objects.tracks.remove(filepath, sql)
                        self._clean_compilation(album_id, sql)
                        self._add2db(filepath, mtime, tag, sql)
                    tracks.remove(filepath)

            except Exception as e:
                print(filepath)
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
        sql.commit()
        sql.close()
        GLib.idle_add(self._finish)

    """
        Add new file to db with tag
        @param filepath as string
        @param file modification time as int
        @param tag as mutagen.File(easy=True)
        @param sql as sqlite cursor
    """
    def _add2db(self, filepath, mtime, tag, sql):
        path = os.path.dirname(filepath)
        popularity = 0
        if path in self._popularities:
            popularity = self._popularities[path]

        keys = tag.keys()
        if "title" in keys:
            title = tag["title"][0]
        else:
            title = os.path.basename(filepath)

        if "artist" in keys:
            artist = format_artist_name(tag["artist"][0])
        else:
            artist = _("Unknown")

        # Vorbis comment uses albumartist for original artist
        # Id3tag uses performer for original artist
        if "albumartist" in keys:
            performer = format_artist_name(tag["albumartist"][0])
        elif "performer" in keys:
            performer = format_artist_name(tag["performer"][0])
        else:
            performer = None

        if "album" in keys:
            album = tag["album"][0]
        else:
            album = _("Unknown")

        if "genre" in keys:
            genre = tag["genre"][0]
        else:
            genre = _("Unknown")

        length = int(tag.info.length)

        if "discnumber" in keys:
            string = tag["discnumber"][0]
            if "/" in string:
                index = string.find("/")
                discnumber = int(string[0:index])
            else:
                try:
                    discnumber = int(string)
                except:
                    discnumber = 0
        else:
            discnumber = 0

        if "tracknumber" in keys:
            string = tag["tracknumber"][0]
            if "/" in string:
                index = string.find("/")
                tracknumber = int(string[0:index])
            else:
                try:
                    tracknumber = int(string)
                except:
                    tracknumber = 0
        else:
            tracknumber = 0

        if "date" in keys:
            try:
                string = tag["date"][0]
                if "-" in string:
                    index = string.find("-")
                    year = int(string[0:index])
                else:
                    year = int(string)
            except:
                year = 0
        else:
            year = 0

        # Get artist id, add it if missing
        artist_id = Objects.artists.get_id(artist, sql)
        if artist_id is None:
            Objects.artists.add(artist, sql)
            artist_id = Objects.artists.get_id(artist, sql)

        if performer:
            # Get performer id, add it if missing
            performer_id = Objects.artists.get_id(performer, sql)
            if performer_id is None:
                Objects.artists.add(performer, sql)
                performer_id = Objects.artists.get_id(performer, sql)
        else:
            performer_id = COMPILATIONS

        # Get genre id, add genre if missing
        genre_id = Objects.genres.get_id(genre, sql)
        if genre_id is None:
            Objects.genres.add(genre, sql)
            genre_id = Objects.genres.get_id(genre, sql)

        album_id = Objects.albums.get_id(album, performer_id, genre_id, sql)
        if album_id is None:
            Objects.albums.add(album, performer_id, genre_id,
                               year, path, popularity, sql)
            album_id = Objects.albums.get_id(album, performer_id,
                                             genre_id, sql)

        # Now we have our album id, check if path doesn't change
        if Objects.albums.get_path(album_id, sql) != path:
            Objects.albums.set_path(album_id, path, sql)

        # Add track to db
        Objects.tracks.add(title, filepath, length,
                           tracknumber, discnumber, artist_id,
                           album_id, mtime, sql)
