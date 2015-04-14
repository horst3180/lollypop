#!/usr/bin/python
# Copyright (c) 2014-2015 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
# Copyright (C) 2010 Jonathan Matthew (replay gain code)
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

from gi.repository import GLib, GObject, Gst, GstPbutils, GstAudio
import random
from os import path

from lollypop.define import Objects, Navigation, NextContext
from lollypop.define import Shuffle
from lollypop.utils import translate_artist_name


class GstPlayFlags:
    GST_PLAY_FLAG_VIDEO = 1 << 0  # We want video output
    GST_PLAY_FLAG_AUDIO = 1 << 1  # We want audio output
    GST_PLAY_FLAG_TEXT = 1 << 3   # We want subtitle output


# Represent current playing track
class CurrentTrack:
        id = None
        title = None
        album_id = None
        album = None
        artist = None
        aartist_id = None
        aartist = None
        genre_id = None
        genre = None
        number = None
        duration = None
        path = None


# Represent playback context
class PlayContext:
        album_id = None
        genre_id = None
        position = None
        next = NextContext.STOP_NONE


# Player object used to manage playback and playlists
class Player(GObject.GObject):

    EPSILON = 0.001

    __gsignals__ = {
        'current-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'seeked': (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        'status-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'volume-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'queue-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'cover-changed': (GObject.SignalFlags.RUN_FIRST, None, (int,str))
    }

    """
        Create a gstreamer bin and listen to signals on bus
    """
    def __init__(self):
        GObject.GObject.__init__(self)
        Gst.init(None)

        self.current = CurrentTrack()
        self.context = PlayContext()
        # Albums in current playlist
        self._albums = None
        # Used by shuffle albums to restore playlist before shuffle
        self._albums_backup = None
        # A user playlist used as current playlist
        self._user_playlist = None
        # Used by shuffle tracks to restore user playlist before shuffle
        self._user_playlist_backup = None
        self._shuffle = Objects.settings.get_enum('shuffle')
        # Tracks already played
        self._shuffle_prev_tracks = []
        # Albums already played
        self._shuffle_albums_backup = []
        # Tracks already played for current album
        self._shuffle_history = {}
        # Party mode
        self._is_party = False
        # Current queue
        self._queue = []
        # Player errors
        self._errors = 0

        self._playbin = Gst.ElementFactory.make('playbin', 'player')
        self._tagreader = GstPbutils.Discoverer.new(10*Gst.SECOND)
        flags = self._playbin.get_property("flags")
        flags &= ~GstPlayFlags.GST_PLAY_FLAG_VIDEO
        self._playbin.set_property("flags", flags)
        self._playbin.connect("about-to-finish",
                              self._on_stream_about_to_finish)
        self._rg_setup()

        Objects.settings.connect('changed::shuffle', self._set_shuffle)

        self._bus = self._playbin.get_bus()
        self._bus.add_signal_watch()
        self._bus.connect('message::error', self._on_bus_error)
        self._bus.connect('message::eos', self._on_bus_eos)
        self._bus.connect('message::stream-start', self._on_stream_start)

    """
        Return informations on file at path
        @param path as str
        @return GstPbutils.DiscovererInfo
    """
    def get_infos(self, path):
        try:
            uri = GLib.filename_to_uri(path)
            infos = self._tagreader.discover_uri(uri)
            return infos
        except:
            return None

    """
        True if player is playing
        @return bool
    """
    def is_playing(self):
        ok, state, pending = self._playbin.get_state(0)
        if ok == Gst.StateChangeReturn.ASYNC:
            return pending == Gst.State.PLAYING
        elif ok == Gst.StateChangeReturn.SUCCESS:
            return state == Gst.State.PLAYING
        else:
            return False

    """
        Emit a "cover-changed" signal
        @param data as str/int
    """
    def announce_cover_update(self, data):
        if isinstance(data, int):
            self.emit("cover-changed", data, "")
        elif isinstance(data, str):
            self.amit("cover-changed", None, str)

    """
        Playback status
        @return Gstreamer state
    """
    def get_status(self):
        ok, state, pending = self._playbin.get_state(0)
        if ok == Gst.StateChangeReturn.ASYNC:
            state = pending
        elif (ok != Gst.StateChangeReturn.SUCCESS):
            state = Gst.State.NULL
        return state

    """
        Stop current track, load track id and play it
        @param track id as int
    """
    def load(self, track_id):
        self._stop()
        if self._load_track(track_id):
            self.play()

    """
        Change player state to PLAYING
    """
    def play(self):
        self._playbin.set_state(Gst.State.PLAYING)
        self.emit("status-changed")

    """
        Change player state to PAUSED
    """
    def pause(self):
        self._playbin.set_state(Gst.State.PAUSED)
        self.emit("status-changed")

    """
        Change player state to STOPPED
    """
    def stop(self):
        self._stop()
        self.emit("status-changed")

    """
        Set PLAYING if PAUSED
        Set PAUSED if PLAYING
    """
    def play_pause(self):
        if self.is_playing():
            self.pause()
        else:
            self.play()

    """
        Play previous track
        If shuffle or party => go backward in shuffle history
        Else => Get previous track in currents albums
    """
    def prev(self):
        track_id = None
        if self._shuffle == Shuffle.TRACKS or self._is_party:
            try:
                track_id = self._shuffle_prev_tracks[-2]
                self._shuffle_prev_tracks.pop()
                self._shuffle_prev_tracks.pop()
            except:
                track_id = None
        elif self.context.position is not None:
            tracks = Objects.albums.get_tracks(self.current.album_id,
                                               self.current.genre_id)
            if self.context.position <= 0:  # Prev album
                pos = self._albums.index(self.current.album_id)
                if pos - 1 < 0:  # we are on last album, go to first
                    pos = len(self._albums) - 1
                else:
                    pos -= 1
                self.current.album_id = self._albums[pos]
                tracks = Objects.albums.get_tracks(self.current.album_id,
                                                   self.current.genre_id)
                self.context.album_id = self.current.album_id
                self.context.position = len(tracks) - 1
                track_id = tracks[self.context.position]
            else:
                self.context.position -= 1
                track_id = tracks[self.context.position]

        if track_id:
            self.load(track_id)

    """
        Play next track
        If shuffle or party => get a random file not already played
        Else => get next track in currents albums
        if force is True (default), don't wait for end of stream
        a fresh sqlite cursor should be pass as sql if we are in a thread
    """
    def next(self, force=True, sql=None):
        # Look first at user queue
        if self._queue:
            track_id = self._queue[0]
            self.del_from_queue(track_id)
            if force:
                self.load(track_id)
            else:
                self._load_track(track_id, sql)
        # Look at user playlist then
        elif self._user_playlist:
            self.context.position += 1
            if self.context.position >= len(self._user_playlist):
                self.context.position = 0
            if force:
                self.load(self._user_playlist[self.context.position])
            else:
                self._load_track(self._user_playlist[self.context.position],
                                 sql)
        # Get a random album/track
        elif self._shuffle in [Shuffle.TRACKS, Shuffle.TRACKS_ARTIST] or\
             self._is_party:
            if self._albums:
                self._shuffle_next(force, sql)
        elif self.context.position is not None and self._albums:
            track_id = None
            tracks = Objects.albums.get_tracks(self.context.album_id,
                                               self.context.genre_id,
                                               sql)
            if self.context.position + 1 >= len(tracks):  # next album
                pos = self._albums.index(self.context.album_id)
                # we are on last album, go to first
                if pos + 1 >= len(self._albums):
                    pos = 0
                else:
                    pos += 1
                self.context.album_id = self._albums[pos]
                self.context.position = 0
                track_id = Objects.albums.get_tracks(self._albums[pos],
                                                     self.context.genre_id,
                                                     sql)[0]
            else:
                self.context.position += 1
                track_id = tracks[self.context.position]

            if force:
                self.load(track_id)
            else:
                self._load_track(track_id, sql)

    """
        Seek current track to position
        @param position as seconds
    """
    def seek(self, position):
        self._playbin.seek_simple(Gst.Format.TIME,
                                  Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
                                  position * Gst.SECOND)
        self.emit("seeked", position)

    """
        Play album
        @param album id as int
        @param genre id as int
    """
    def play_album(self, album_id, genre_id=None):
        # Empty user playlist
        self._user_playlist = None
        # Get first track from album
        track_id = Objects.albums.get_tracks(album_id, genre_id)[0]
        Objects.player.load(track_id)
        if not Objects.player.is_party():
            if genre_id:
                self.set_albums(self.current.id,
                                self.current.aartist_id,
                                genre_id)
            else:
                self.set_album(album_id)

    """
        Return party ids
        @return [ids as int]
    """
    def get_party_ids(self):
        party_settings = Objects.settings.get_value('party-ids')
        ids = []
        genre_ids = Objects.genres.get_ids()
        for setting in party_settings:
            if isinstance(setting, int) and\
               setting in genre_ids:
                ids.append(setting)
        return ids

    """
        Set party mode on if party is True
        Play a new random track if not already playing
        @param party as bool
    """
    def set_party(self, party):
        self._shuffle_prev_tracks = []
        self._shuffle_history = {}
        self._shuffle_albums_backup = []
        self._user_playlist = None
        if party:
            self.context.next = NextContext.STOP_NONE
            self._rgvolume.props.album_mode = 0
        else:
            self._rgvolume.props.album_mode = 1
        self._is_party = party
        self._shuffle_prev_tracks = []
        if party:
            party_ids = self.get_party_ids()
            if len(party_ids) > 0:
                self._albums = Objects.albums.get_party_ids(party_ids)
            else:
                self._albums = Objects.albums.get_ids()
            # Start a new song if not playing
            if not self.is_playing() and self._albums:
                track_id = self._get_random()
                self.load(track_id)
        else:
            # We need to put some context, take first available genre
            if self.current.id:
                self.set_albums(self.current.id,
                                self.current.aartist_id, None)

    """
        True if party mode on
        @return bool
    """
    def is_party(self):
        return self._is_party

    """
        Set album as current album list (for next/prev)
        Set track as current track in album
        @param album_id as int
    """
    def set_album(self, album_id):
        self._albums = [album_id]
        self.context.album_id = album_id
        self.context.genre_id = None
        tracks = Objects.albums.get_tracks(album_id, None)
        self.context.position = tracks.index(self.current.id)

    """
        Set album list (for next/prev)
        @param track id as int
        @param artist id as int
        @param genre id as int
    """
    def set_albums(self, track_id, artist_id, genre_id):
        # Invalid track
        if track_id is None:
            return
        album_id = Objects.tracks.get_album_id(track_id)
        self._albums = []
        self._shuffle_prev_tracks = []
        self._shuffle_history = {}
        self._shuffle_albums_backup = []
        self.context.genre_id = genre_id

        # When shuffle from artist is active, we want only artist's albums,
        # we need to ignore genre
        if self._shuffle in [Shuffle.TRACKS_ARTIST, Shuffle.ALBUMS_ARTIST]:
            genre_id = None

        # We are not playing a user playlist anymore
        self._user_playlist = None
        # We are in all artists
        if genre_id == Navigation.ALL or artist_id == Navigation.ALL:
            self._albums = Objects.albums.get_compilations(Navigation.ALL)
            self._albums += Objects.albums.get_ids()
        # We are in popular view, add populars albums
        elif genre_id == Navigation.POPULARS:
            self._albums = Objects.albums.get_populars()
        # Random tracks/albums for genre
        elif self._shuffle in [Shuffle.TRACKS, Shuffle.ALBUMS]:
            self._albums = Objects.albums.get_ids(None, genre_id)
        # Random tracks/albums for artist
        elif self._shuffle in [Shuffle.TRACKS_ARTIST, Shuffle.ALBUMS_ARTIST]:
            self._albums = Objects.albums.get_ids(artist_id, genre_id)
        # Add all albums for genre
        else:
            self._albums = Objects.albums.get_compilations(genre_id)
            self._albums += Objects.albums.get_ids(None, genre_id)

        self.context.album_id = album_id
        tracks = Objects.albums.get_tracks(album_id, genre_id)
        self.context.position = tracks.index(track_id)
        self.context.genre_id = genre_id
        # Shuffle album list if needed
        self._shuffle_playlist()

    """
        Append track to queue,
        remove previous track if exist
        @param track id as int
    """
    def append_to_queue(self, track_id):
        if track_id in self._queue:
            self._queue.remove(track_id)
        self._queue.append(track_id)
        self.emit("queue-changed")

    """
        Prepend track to queue,
        remove previous track if exist
        @param track id as int
    """
    def prepend_to_queue(self, track_id):
        if track_id in self._queue:
            self._queue.remove(track_id)
        self._queue.insert(0, track_id)
        self.emit("queue-changed")

    """
        Remove track from queue
        @param track id as int
    """
    def del_from_queue(self, track_id):
        if track_id in self._queue:
            self._queue.remove(track_id)
            self.emit("queue-changed")

    """
        Set queue
        @param [ids as int]
    """
    def set_queue(self, new_queue):
        self._queue = new_queue
        self.emit("queue-changed")

    """
        Return queue
        @return [ids as int]
    """
    def get_queue(self):
        if self._queue:
            return self._queue
        else:
            return []

    """
        True if track_id exist in queue
        @param track id as int
        @return bool
    """
    def is_in_queue(self, track_id):
        if self._queue:
            return track_id in self._queue
        else:
            return False

    """
        Return track position in queue
        @param track id as int
        @return position as int
    """
    def get_track_position(self, track_id):
        return self._queue.index(track_id)+1

    """
        Return bin playback position
        @return position as int
    """
    def get_position_in_track(self):
        position = self._playbin.query_position(Gst.Format.TIME)[1] / 1000
        return position*60

    """
        Set user playlist as current playback playlist
        @param array of track id as int
        @param starting track id as int
    """
    def set_user_playlist(self, tracks, track_id):
        self._user_playlist = tracks
        self._albums = None
        self.context.album_id = None
        self.context.position = self._user_playlist.index(track_id)
        self._shuffle_playlist()

    """
        Restore player state
    """
    def restore_state(self):
        track_id = Objects.settings.get_value('track-id').get_int32()
        if Objects.settings.get_value('save-state') and track_id > 0:
            self._load_track(track_id)
            self.set_albums(track_id, Navigation.ALL, Navigation.ALL)
            self.emit('current-changed')

    """
        Return player volume rate
        @return rate as double
    """
    def get_volume(self):
        return self._playbin.get_volume(GstAudio.StreamVolumeFormat.LINEAR)

    """
        Set player volume rate
        @param rate as double
    """
    def set_volume(self, rate):
        self._playbin.set_volume(GstAudio.StreamVolumeFormat.LINEAR, rate)
        self.emit('volume-changed')
    
#######################
# PRIVATE             #
#######################

    """
        Stop current track (for track change)
    """
    def _stop(self):
        self._playbin.set_state(Gst.State.NULL)

    """
        Add a track to shuffle history
        @param track id as int
        @param album id as int
    """
    def _add_to_shuffle_history(self, track_id, album_id):
        if self.current.album_id not in self._shuffle_history.keys():
            self._shuffle_history[self.current.album_id] = []
        self._shuffle_history[self.current.album_id].append(self.current.id)

    """
        Shuffle/Un-shuffle playlist based on shuffle setting
    """
    def _shuffle_playlist(self):
        if self._shuffle in [Shuffle.ALBUMS, Shuffle.ALBUMS_ARTIST]:
            # No albums shuffle when playing a user playlist
            if self._user_playlist_backup:
                self._user_playlist = self._user_playlist_backup
                self.context.position = self._user_playlist.index(
                                                              self.current.id)
                self._user_playlist_backup = None
            # Shuffle albums list
            if self._albums:
                self._albums_backup = list(self._albums)
                random.shuffle(self._albums)
        elif self._shuffle in [Shuffle.TRACKS, Shuffle.TRACKS_ARTIST]:
            # Shuffle user playlist
            if self._user_playlist:
                self._user_playlist_backup = list(self._user_playlist)
                current = self._user_playlist.pop(self.context.position)
                random.shuffle(self._user_playlist)
                self._user_playlist.insert(0, current)
                self.context.position = 0
            # Shuffle Tracks, just add current to history
            elif self.current.id:
                self._add_to_shuffle_history(self.current.id,
                                             self.current.album_id)

        # Unshuffle
        elif self._shuffle == Shuffle.NONE:
            if self._user_playlist_backup:
                self._user_playlist = self._user_playlist_backup
                self.context.position = self._user_playlist.index(
                                                              self.current.id)
                self._user_playlist_backup = None
            elif self._albums_backup:
                self._albums = self._albums_backup
                self._albums_backup = None
          

    """
        Set shuffle mode to gettings value
        @param settings as Gio.Settings, value as str
    """
    def _set_shuffle(self, settings, value):
        self._shuffle = Objects.settings.get_enum('shuffle')
        self._shuffle_albums_backup = []
        self._shuffle_history = {}
        self._shuffle_prev_tracks = []

        if self._shuffle in [Shuffle.TRACKS, Shuffle.TRACKS_ARTIST] or\
           self._user_playlist:
            self._rgvolume.props.album_mode = 0
        else:
            self._rgvolume.props.album_mode = 1
        self.set_albums(self.current.id,
                        self.current.aartist_id,
                        self.context.genre_id)

    """
        Setup replaygain
    """
    def _rg_setup(self):
        self._rgfilter = Gst.ElementFactory.make("bin", "bin")

        self._rg_audioconvert1 = Gst.ElementFactory.make("audioconvert",
                                                         "audioconvert")
        self._rg_audioconvert2 = Gst.ElementFactory.make("audioconvert",
                                                         "audioconvert2")

        self._rgvolume = Gst.ElementFactory.make("rgvolume",
                                                 "rgvolume")
        self._rglimiter = Gst.ElementFactory.make("rglimiter",
                                                  "rglimiter")
        self._rg_audiosink = Gst.ElementFactory.make("autoaudiosink",
                                                     "autoaudiosink")

        if not self._rgfilter or not self._rg_audioconvert1 or\
           not self._rg_audioconvert2 or not self._rgvolume or\
           not self._rglimiter or not self._rg_audiosink:
            print("Replay Gain not available, ")
            print("please check your gstreamer installation...")
            return

        self._rgvolume.props.pre_amp = Objects.settings.get_value(
                                            "replaygain").get_double()

        self._rgfilter.add(self._rgvolume)
        self._rgfilter.add(self._rg_audioconvert1)
        self._rgfilter.add(self._rg_audioconvert2)
        self._rgfilter.add(self._rglimiter)
        self._rgfilter.add(self._rg_audiosink)

        self._rg_audioconvert1.link(self._rgvolume)
        self._rgvolume.link(self._rg_audioconvert2)
        self._rgvolume.link(self._rglimiter)
        self._rg_audioconvert2.link(self._rg_audiosink)

        self._rgfilter.add_pad(Gst.GhostPad.new(
                                "sink",
                                self._rg_audioconvert1.get_static_pad("sink")))

        self._playbin.set_property("audio-sink", self._rgfilter)

    """
        Next track in shuffle mode
        if force, stop current track
        a fresh sqlite cursor should be passed as sql if we are in a thread
        @param bool, sqlite cursor
    """
    def _shuffle_next(self, force=False, sql=None):
        track_id = self._get_random(sql)
        # Need to clear history
        if not track_id:
            self._albums = self._shuffle_albums_backup
            self._shuffle_prev_tracks = []
            self._shuffle_history = {}
            self._shuffle_albums_backup = []
            self._shuffle_next(force)
            return

        if force:
            self.load(track_id)
        else:
            self._load_track(track_id, sql)

    """
        Return a random track and make sure it has never been played
        @param sqlite cursor as sql if running in a thread
    """
    def _get_random(self, sql=None):
        for album_id in sorted(self._albums,
                               key=lambda *args: random.random()):
            tracks = Objects.albums.get_tracks(album_id,
                                               self.current.genre_id,
                                               sql)
            for track in sorted(tracks, key=lambda *args: random.random()):
                if album_id not in self._shuffle_history.keys() or\
                   track not in self._shuffle_history[album_id]:
                    return track
            # No new tracks for this album, remove it
            # If albums not in shuffle history, it's not present
            # in db anymore (update since shuffle set)
            if album_id in self._shuffle_history.keys():
                self._shuffle_history.pop(album_id)
                self._shuffle_albums_backup.append(album_id)
            self._albums.remove(album_id)

        return None

    """
        On stream start
        Emit "current-changed" to notify others components
    """
    def _on_stream_start(self, bus, message):
        self.emit("current-changed")
        self._errors = 0
        # Add track to shuffle history if needed
        if self._shuffle != Shuffle.NONE or self._is_party:
            self._shuffle_prev_tracks.append(self.current.id)
            self._add_to_shuffle_history(self.current.id,
                                         self.current.album_id)

    """
        On error, next()
    """
    def _on_bus_error(self, bus, message):
        print("Error playing: ", self.current.path)
        self.next(True)
        return False

    """
        On eos, force loading if queue fails,
        if on_stream_about_to_finish never get send
    """
    def _on_bus_eos(self, bus, message):
        self.load(self.current.id)

    """
        When stream is about to finish, switch to next track without gap
    """
    def _on_stream_about_to_finish(self, obj):
        self._previous_track_id = self.current.id
        # We are in a thread, we need to create a new cursor
        sql = Objects.db.get_cursor()
        self.next(False, sql)
        # Add populariy if we listen to the song
        album_id = Objects.tracks.get_album_id(self._previous_track_id, sql)
        try:
            Objects.albums.set_more_popular(album_id, sql)
        except:
            pass
        sql.close()

    """
        On error, try 3 more times playing a track
    """
    def _on_errors(self):
        self._errors += 1
        if self._errors < 3:
            GLib.idle_add(self.next, True)
        else:
            self.current = CurrentTrack()
            GLib.idle_add(self.stop)
            GLib.idle_add(self.emit, 'current-changed')

    """
        Load track
        @param track id as int, sqlite cursor
        @return False if track not loaded
    """
    def _load_track(self, track_id, sql=None):
        # Stop if needed
        if self.context.next == NextContext.STOP_TRACK:
            GLib.idle_add(self.stop)
            return False

        # Stop if album changed
        new_album_id = Objects.tracks.get_album_id(
                                                track_id,
                                                sql)
        if self.context.next == NextContext.STOP_ALBUM and\
           self.current.album_id != new_album_id:
            GLib.idle_add(self.stop)
            return False

        # Stop if aartist changed
        new_aartist_id = Objects.tracks.get_aartist_id(
                                                track_id,
                                                sql)
        if self.context.next == NextContext.STOP_ARTIST and\
           self.current.aartist_id != new_aartist_id:
            GLib.idle_add(self.stop)
            return False

        self.current.id = track_id
        self.current.title = Objects.tracks.get_name(
                                                self.current.id,
                                                sql)
        self.current.album_id = new_album_id
        self.current.album = Objects.albums.get_name(
                                                self.current.album_id,
                                                sql)
        self.current.aartist_id = new_aartist_id
        self.current.aartist = translate_artist_name(
                                        Objects.artists.get_name(
                                                self.current.aartist_id,
                                                sql))
        artist_name = ""
        for artist_id in Objects.tracks.get_artist_ids(self.current.id,
                                                       sql):
            artist_name += translate_artist_name(
                            Objects.artists.get_name(artist_id, sql)) + ", "
        self.current.artist = artist_name[:-2]

        self.current.genre = Objects.albums.get_genre_name(
                                                self.current.album_id,
                                                sql)
        self.current.duration = Objects.tracks.get_length(self.current.id, sql)
        self.current.number = Objects.tracks.get_number(self.current.id, sql)
        self.current.path = Objects.tracks.get_path(self.current.id, sql)
        if path.exists(self.current.path):
            try:
                self._playbin.set_property('uri',
                                           GLib.filename_to_uri(
                                                        self.current.path))
            except:  # Gstreamer error, stop
               self._on_errors()
               return False
        else:
            print("File doesn't exist: ", self.current.path)
            self._on_errors()
            return False
        return True
