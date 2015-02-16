#!/usr/bin/python
# Copyright (c) 2014-2015 Cedric Bellegarde <gnumdk@gmail.com>
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

from gi.repository import Gtk, Gdk, GLib, Gio, GObject, Gst, GstAudio
import random
from os import path

from lollypop.define import *
from lollypop.utils import translate_artist_name
from lollypop.database import Database

class CurrentTrack:
    def __init__(self):
        self.id = None
        self.title = None
        self.album_id = None
        self.album = None
        self.artist_id = None
        self.artist = None
        self.performer_id = None
        self.performer = None
        self.genre_id = None
        self.genre = None
        self.number = None
        self.duration = None
        self.path = None

class Player(GObject.GObject):

    EPSILON = 0.001
    
    __gsignals__ = {
        'current-changed': (GObject.SIGNAL_RUN_FIRST, None, ()),
        'seeked': (GObject.SIGNAL_RUN_FIRST, None, (int,)),
        'status-changed': (GObject.SIGNAL_RUN_FIRST, None, ()),
        'queue-changed': (GObject.SIGNAL_RUN_FIRST, None, ()),
        'cover-changed': (GObject.SIGNAL_RUN_FIRST, None, (int,))
    }

    """
        Create a gstreamer bin and listen to signals on bus
    """
    def __init__(self):
        GObject.GObject.__init__(self)
        Gst.init(None)

        self.current = CurrentTrack()
        self._albums = None # Albums in current playlist
        self._albums_backup = None # Used by shuffle albums to restore playlist before shuffle
        self._user_playlist = None # A user playlist used as current playlist
        self._user_playlist_backup = None # Used by shuffle tracks to restore user playlist before shuffle
        self._shuffle = Objects.settings.get_enum('shuffle')
        self._shuffle_tracks_history = [] # Tracks already played
        self._shuffle_albums_backup = [] # Albums already played
        self._shuffle_album_tracks_history = [] # Tracks already played for current album
        self._party = False
        self._party_ids = None
        self._queue = []

        self._playbin = Gst.ElementFactory.make('playbin', 'player')
        self._playbin.connect("about-to-finish", self._on_stream_about_to_finish)
        self._rg_setup()
        
        Objects.settings.connect('changed::shuffle', self._set_shuffle)
        
        self._bus = self._playbin.get_bus()
        self._bus.add_signal_watch()
        self._bus.connect('message::error', self._on_bus_error)
        self._bus.connect('message::eos', self._on_bus_eos)
        self._bus.connect('message::stream-start', self._on_stream_start)
        
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
        @param album id as int
    """
    def announce_cover_update(self, album_id):
        self.emit("cover-changed", album_id)
        
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
        self.stop()
        self._load_track(track_id)
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
        self._playbin.set_state(Gst.State.NULL)

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
        if self._shuffle == SHUFFLE_TRACKS or self._party:
            try:
                track_id = self._shuffle_tracks_history[-2]
                self._shuffle_tracks_history.pop()
                self._shuffle_tracks_history.pop()
            except Exception as e:
                track_id = None
        elif self.current.number != -1:
            tracks = Objects.albums.get_tracks(self.current.album_id)
            if self.current.number <= 0 : #Prev album
                pos = self._albums.index(self.current.album_id)
                if pos - 1 < 0: #we are on last album, go to first
                    pos = len(self._albums) - 1
                else:
                    pos -= 1
                self.current.album_id = self._albums[pos]
                tracks = Objects.albums.get_tracks(self.current.album_id)
                self.current.number = len(tracks) - 1
                track_id = tracks[self.current.number]
            else:
                self.current.number -= 1
                track_id = tracks[self.current.number]
    
        if track_id:            
            self.load(track_id)
    
    """
        Play next track
        If shuffle or party => get a random file not already played
        Else => get next track in currents albums
        if force is True (default), don't wait for end of stream
        a fresh sqlite cursor should be pass as sql if we are in a thread
    """
    def next(self, force = True, sql = None):
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
            self.current.number += 1
            if self.current.number >= len(self._user_playlist):
                self.current.number = 0
            if force:
                self.load(self._user_playlist[self.current.number])
            else:
                self._load_track(self._user_playlist[self.current.number], sql)
        # Get a random album/track
        elif self._shuffle == SHUFFLE_TRACKS or self._party:
            self._shuffle_next(force, sql)
        elif self.current.number != None:
            track_id = None
            tracks = Objects.albums.get_tracks(self.current.album_id, sql)
            if self.current.number + 1 >= len(tracks): #next album
                pos = self._albums.index(self.current.album_id)
                if pos +1 >= len(self._albums): #we are on last album, go to first
                    pos = 0
                else:
                    pos += 1
                self.current.album_id = self._albums[pos]
                self.current.number = 0
                track_id = Objects.albums.get_tracks(self._albums[pos], sql)[0]
            else:
                self.current.number += 1
                track_id = tracks[self.current.number]

            if force:
                self.load(track_id)
            else:
                self._load_track(track_id, sql)

    """
        Seek current track to position
        @param position as seconds
    """
    def seek(self, position):
        self._playbin.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, position * Gst.SECOND)
        self.emit("seeked", position)


    """
        Play album
        @param album id as int
    """
    def play_album(self, album_id):
        # Get first track from album
        track_id = Objects.albums.get_tracks(album_id)[0]
        Objects.player.load(track_id)
        if not Objects.player.is_party():
            Objects.player.set_album(album_id)

    """
        Set party mode on if party is True
        Play a new random track if not already playing
        @param party as bool
    """
    def set_party(self, party):
        self._shuffle_tracks_history = []
        self._shuffle_album_tracks_history = []
        self._shuffle_albums_backup = []
        self._user_playlist = None
        if party:
            self._rgvolume.props.album_mode = 0
        else:
            self._rgvolume.props.album_mode = 1
        self._party = party
        self._shuffle_tracks_history = []
        if party:
            if len(self._party_ids) > 0:
                self._albums = Objects.albums.get_party_ids(self._party_ids)
            else:
                self._albums = Objects.albums.get_ids()
            # Start a new song if not playing
            if not self.is_playing():
                track_id = self._get_random()
                self.load(track_id)
        else:
            genre_id = Objects.albums.get_genre_id(self.current.album_id)
            self.set_albums(self.current.artist_id, genre_id, True)

    """
        Set party ids to ids
        Party ids are genres_id (and specials ids) used to populate party mode
        @param [ids as int]
    """
    def set_party_ids(self, ids):
        self._party_ids = ids

    """
        Return party ids
        @return [ids as int]
    """
    def get_party_ids(self):
        return self._party_ids

    """
        True if party mode on
        @return bool
    """
    def is_party(self):
        return self._party

    """
        Set album as current album list (for next/prev)
        Set track as current track in album
        @param album_id as int
    """
    def set_album(self, album_id):
        self._albums = [ album_id ]

    """
        Set album list (for next/prev)
        Set track as current track in albums
        @param artist id as int
        @param genre id as int
        @param limit_to_artist as bool => only load artist tracks
    """
    def set_albums(self, artist_id, genre_id, limit_to_artist):
        self._albums = []
        self._shuffle_tracks_history = []
        self._shuffle_album_tracks_history = []
        self._shuffle_albums_backup = []
        self._user_playlist = None # We are not playing a user playlist anymore
        # We are in all artists
        if genre_id == ALL or artist_id == ALL:
            self._albums = Objects.albums.get_compilations(ALL)
            self._albums += Objects.albums.get_ids()
        # We are in popular view, add populars albums
        elif genre_id == POPULARS:
            self._albums = Objects.albums.get_populars()
        elif limit_to_artist:
            self._albums = Objects.albums.get_ids(artist_id, genre_id)
        else:
            # We are in album/artist view, add all albums from current genre
            self._albums = Objects.albums.get_compilations(genre_id)
            self._albums += Objects.albums.get_ids(None, genre_id)

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
            if len(self._queue) == 0:
                self._queue = None
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
        self._shuffle_playlist()
    
#######################
# PRIVATE             #
#######################

    """
        Shuffle/Un-shuffle playlist based on shuffle setting
    """
    def _shuffle_playlist(self):
        # Shuffle album list or restore unshuffled list
        if self._shuffle == SHUFFLE_ALBUMS and self._albums:
            self._albums_backup = list(self._albums)
            random.shuffle(self._albums)
        # Shuffle playlist
        elif self._shuffle == SHUFFLE_TRACKS and self._user_playlist:
            self._user_playlist_backup = list(self._user_playlist)
            random.shuffle(self._user_playlist)
        # When shuffle none or shuffle albums and a user playlist is defined
        # Unshuffle
        elif self._shuffle in [ SHUFFLE_NONE, SHUFFLE_ALBUMS]:
            if self._albums_backup:
                self._albums = self._albums_backup
                self._albums_backup = None
            if self._user_playlist_backup:
                self._user_playlist = self._user_playlist_backup
                self._user_playlist_backup = None

    """
        Set shuffle mode to gettings value
        @param settings as Gio.Settings, value as str
    """
    def _set_shuffle(self, settings, value):
        self._shuffle = Objects.settings.get_enum('shuffle')
        self._shuffle_albums_backup = []
        self._shuffle_album_tracks_history = []
        self._shuffle_tracks_history = []

        if self._shuffle == SHUFFLE_TRACKS or self._user_playlist:
            self._rgvolume.props.album_mode = 0
        else:
            self._rgvolume.props.album_mode = 1
        
        # Shuffle album list or restore unshuffled list
        self._shuffle_playlist()

        # Restore position in user playlist
        if self._shuffle != SHUFFLE_TRACKS and self._user_playlist:
            self.current.number = self._user_playlist.index(self.current.id)
        # Restore position in current album
        elif self._shuffle in [ SHUFFLE_NONE, SHUFFLE_ALBUMS] and self.current.id:
            tracks = Objects.albums.get_tracks(self.current.album_id)
            self.current.number = tracks.index(self.current.id)
        # Add current track too shuffle history
        elif self.current.id:
            self._shuffle_tracks_history.append(self.current.id)
            
    """
        Setup replaygain
    """
    def _rg_setup(self):
        self._rgfilter = Gst.ElementFactory.make("bin", "bin")

        self._rg_audioconvert1 = Gst.ElementFactory.make("audioconvert", "audioconvert")
        self._rg_audioconvert2 = Gst.ElementFactory.make("audioconvert", "audioconvert2")
        
        self._rgvolume = Gst.ElementFactory.make("rgvolume", "rgvolume")
        self._rglimiter = Gst.ElementFactory.make("rglimiter", "rglimiter")
        self._rg_audiosink = Gst.ElementFactory.make("autoaudiosink", "autoaudiosink")

        if not self._rgfilter or not self._rg_audioconvert1 or not self._rg_audioconvert2\
        or not self._rgvolume or not self._rglimiter or not self._rg_audiosink:
            print("Replay Gain not available, please check your gstreamer installation...")
            return

        self._rgvolume.props.pre_amp = 0.0

        self._rgfilter.add(self._rgvolume)
        self._rgfilter.add(self._rg_audioconvert1)
        self._rgfilter.add(self._rg_audioconvert2)
        self._rgfilter.add(self._rglimiter)
        self._rgfilter.add(self._rg_audiosink)

        self._rg_audioconvert1.link(self._rgvolume)
        self._rgvolume.link(self._rg_audioconvert2)
        self._rgvolume.link(self._rglimiter)
        self._rg_audioconvert2.link(self._rg_audiosink)
        
        self._rgfilter.add_pad(Gst.GhostPad.new("sink", self._rg_audioconvert1.get_static_pad("sink")))
        
        self._playbin.set_property("audio-sink", self._rgfilter)

    """
        Next track in shuffle mode
        if force, stop current track
        a fresh sqlite cursor should be passed as sql if we are in a thread
        @param bool, sqlite cursor
    """
    def _shuffle_next(self, force = False, sql = None):
        track_id = self._get_random(sql)
        # Need to clear history
        if not track_id:
            self._albums = self._shuffle_albums_backup
            self._shuffle_tracks_history = []
            self._shuffle_album_tracks_history = []
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
    def _get_random(self, sql = None):
        for album_id in sorted(self._albums, key=lambda *args: random.random()):
            tracks = Objects.albums.get_tracks(album_id, sql)
            for track in sorted(tracks, key=lambda *args: random.random()):
                if not track in self._shuffle_album_tracks_history:
                    return track
            # No new tracks for this album, remove it
            self._albums.remove(album_id)
            for track_id in Objects.albums.get_tracks(album_id):
                self._shuffle_album_tracks_history.remove(track_id)
            self._shuffle_albums_backup.append(album_id)

        return None

    """
        On stream start
        Emit "current-changed" to notify others components
    """
    def _on_stream_start(self, bus, message):
        self.emit("current-changed")
        # Add track to shuffle history if needed
        if self._shuffle != SHUFFLE_NONE or self._party:
            self._shuffle_tracks_history.append(self.current.id)
            self._shuffle_album_tracks_history.append(self.current.id)


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
        Objects.albums.set_more_popular(album_id, sql)
        sql.close()
        
    """
        Load track
        @param track id as int, sqlite cursor
    """
    def _load_track(self, track_id, sql = None):
        self.current.id = track_id
        self.current.title = Objects.tracks.get_name(self.current.id, sql)
        self.current.album_id = Objects.tracks.get_album_id(self.current.id, sql)
        self.current.album = Objects.albums.get_name(self.current.album_id, sql)
        self.current.performer_id = Objects.tracks.get_performer_id(self.current.id, sql)
        self.current.performer = translate_artist_name(Objects.artists.get_name(self.current.performer_id, sql))
        self.current.artist_id = Objects.tracks.get_artist_id(self.current.id, sql)
        self.current.artist = translate_artist_name(Objects.artists.get_name(self.current.artist_id, sql))
        self.current.genre_id = Objects.albums.get_genre_id(self.current.album_id, sql)
        self.current.genre = Objects.genres.get_name(self.current.genre_id, sql)
        self.current.duration = Objects.tracks.get_length(self.current.id, sql)
        
        if self._user_playlist:
            self.current.number = self._user_playlist.index(track_id)
        else:
            tracks = Objects.albums.get_tracks(self.current.album_id, sql)
            self.current.number = tracks.index(self.current.id)
            
        self.current.path = Objects.tracks.get_path(self.current.id, sql)
        if path.exists(self.current.path):
            self._playbin.set_property('uri', GLib.filename_to_uri(self.current.path))
        else:
            print("File doesn't exist: ", self.current.path)
            self.next(True, sql)
