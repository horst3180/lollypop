#!/usr/bin/python
# Copyright (c) 2014 Cedric Bellegarde <gnumdk@gmail.com>
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

from lollypop.config import *
from lollypop.database import Database


class PlaybackStatus:
    PLAYING = 0
    PAUSED = 1
    STOPPED = 2

class Player(GObject.GObject):
	
	EPSILON = 0.001
	
	__gsignals__ = {
        'current-changed': (GObject.SIGNAL_RUN_FIRST, None, (int,)),
        'position-changed': (GObject.SIGNAL_RUN_FIRST, None, (int,)),
        'playback-status-changed': (GObject.SIGNAL_RUN_FIRST, None, ()),
        'playlist-changed': (GObject.SIGNAL_RUN_FIRST, None, ()),
        'cover-changed': (GObject.SIGNAL_RUN_FIRST, None, (int,))
    }

	"""
		Create a gstreamer bin and listen to signals on bus
	"""
	def __init__(self):
		GObject.GObject.__init__(self)
		Gst.init(None)

		self._current_track_number = -1
		self._current_track_album_id = -1
		self._current_track_id = -1
		self._albums = []
		self._timeout = None
		self._shuffle = False
		self._shuffle_tracks_history = []
		self._shuffle_albums_history = []
		self._party = False
		self._party_ids = []
		self._playlist = []

		self._playbin = Gst.ElementFactory.make('playbin', 'player')
		self._playbin.connect("about-to-finish", self._on_stream_about_to_finish)
		self._rg_setup()
		
		
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
		@return
			- PlaybackStatus.STOPPED
			- PlaybackStatus.PLAYING
			- PlaybackStatus.PAUSED
	"""
	def get_playback_status(self):
		ok, state, pending = self._playbin.get_state(0)
		if ok == Gst.StateChangeReturn.ASYNC:
			state = pending
		elif (ok != Gst.StateChangeReturn.SUCCESS):
			return PlaybackStatus.STOPPED

		if state == Gst.State.PLAYING:
			return PlaybackStatus.PLAYING
		elif state == Gst.State.PAUSED:
			return PlaybackStatus.PAUSED
		else:
			return PlaybackStatus.STOPPED


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
		if not self._timeout:
			self._timeout = GLib.timeout_add(1000, self._update_position)
		self.emit("playback-status-changed")

	"""
		Change player state to PAUSED
	"""
	def pause(self):
		self._playbin.set_state(Gst.State.PAUSED)
		self.emit("playback-status-changed")
		if self._timeout:
			GLib.source_remove(self._timeout)
			self._timeout = None

	"""
		Change player state to STOPPED
	"""
	def stop(self):
		self._playbin.set_state(Gst.State.NULL)
		if self._timeout:
			GLib.source_remove(self._timeout)
			self._timeout = None

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
		if self._shuffle or self._party:
			try:
				track_id = self._shuffle_tracks_history[-2]
				self._shuffle_tracks_history.pop()
				self._shuffle_tracks_history.pop()
			except Exception as e:
				track_id = None
		elif self._current_track_number != -1:
			tracks = Objects["albums"].get_tracks(self._current_track_album_id)
			if self._current_track_number <=0 : #Prev album
				pos = self._albums.index(self._current_track_album_id)
				if pos - 1 < 0: #we are on last album, go to first
					pos = len(self._albums) - 1
				else:
					pos -= 1
				self._current_track_album_id = self._albums[pos]
				tracks = Objects["albums"].get_tracks(self._current_track_album_id)
				self._current_track_number = len(tracks) - 1
				track_id = tracks[self._current_track_number]
			else:
				self._current_track_number -= 1
				track_id = tracks[self._current_track_number]
	
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
		# Look first at user playlist
		if len(self._playlist) > 0:
			track_id = self._playlist.pop(0)
			if force:
				self.load(track_id)
			else:
				self._load_track(track_id, sql)
		# Get a random album/track
		elif self._shuffle or self._party:
			self._shuffle_next(force, sql)
		elif self._current_track_number != -1:
			track_id = None
			tracks = Objects["albums"].get_tracks(self._current_track_album_id, sql)
			if self._current_track_number + 1 >= len(tracks): #next album
				pos = self._albums.index(self._current_track_album_id)
				if pos +1 >= len(self._albums): #we are on last album, go to first
					pos = 0
				else:
					pos += 1
				self._current_track_album_id = self._albums[pos]
				self._current_track_number = 0
				track_id = Objects["albums"].get_tracks(self._albums[pos], sql)[0]
			else:
				self._current_track_number += 1
				track_id = tracks[self._current_track_number]

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

	"""
		Return current track id
		@return track id as int
	"""
	def get_current_track_id(self):
		return self._current_track_id

	"""
		Set shuffle mode if suffle is True
		@param shuffle as bool
	"""
	def set_shuffle(self, shuffle):
		if shuffle:
			self._rgvolume.props.album_mode = 0
		else:
			self._rgvolume.props.album_mode = 1
		self._shuffle_tracks_history = []
		self._shuffle = shuffle
		if not shuffle and self._current_track_id != -1:
			album_id = Objects["tracks"].get_album_id(self._current_track_id)
			artist_id = Objects["artists"].get_id(album_id)
			genre_id = Objects["albums"].get_genre(album_id)
			self.set_albums(artist_id, genre_id, self._current_track_id)

	"""
		Set party mode on if party is True
		Play a new random track if not already playing
		@param party as bool
	"""
	def set_party(self, party):
		if party:
			self._rgvolume.props.album_mode = 0
		else:
			self._rgvolume.props.album_mode = 1
		self._party = party
		self._shuffle_tracks_history = []
		if party:
			if len(self._party_ids) > 0:
				self._albums = Objects["albums"].get_party_ids(self._party_ids)
			else:
				self._albums = Objects["albums"].get_ids()
			# Start a new song if not playing
			if not self.is_playing():
				track_id = self._get_random()
				self.load(track_id)
				self._current_track_album_id = Objects["tracks"].get_album_id(track_id)
		else:
			album_id = Objects["tracks"].get_album_id(self._current_track_id)
			artist_id = Objects["artists"].get_id(album_id)
			genre_id = Objects["albums"].get_genre(album_id)
			self.set_albums(artist_id, genre_id, self._current_track_id)

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
		Set album list (for next/prev)
		@param artist id as int, genre id as int, track id as int
	"""
	def set_albums(self, artist_id, genre_id, track_id):
		filepath = Objects["tracks"].get_path(track_id)
		if path.exists(filepath):
			self._albums = []
			# We are in All artists
			if genre_id == ALL or artist_id == ALL:
				self._albums = Objects["albums"].get_compilations(ALL)
				self._albums += Objects["albums"].get_ids()
			# We are in popular view, add populars albums
			elif genre_id == POPULARS:
				self._albums = Objects["albums"].get_populars()
			else:
			# We are in album/artist view, add all albums from current genre
				self._albums = Objects["albums"].get_compilations(genre_id)
				self._albums += Objects["albums"].get_ids(None, genre_id)
			album_id = Objects["tracks"].get_album_id(track_id)
			tracks = Objects["albums"].get_tracks(album_id)
			self._current_track_number = tracks.index(track_id) 
			self._current_track_album_id = album_id

	"""
		Empty albums list
	"""
	def clear_albums(self):
		self._albums = []

	"""
		Convert seconds to a pretty string
		@param seconds as int
	"""
	def seconds_to_string(self, duration):
		seconds = duration
		minutes = seconds // 60
		seconds %= 60

		return '%i:%02i' % (minutes, seconds)

	"""
		Add track to playlist
		@param track id as int
	"""
	def add_to_playlist(self, track_id):
		self._playlist.append(track_id)

	"""
		Remove track from playlist
		@param track id as int
	"""
	def del_from_playlist(self, track_id):
		self._playlist.remove(track_id)

	"""
		Set playlist
		@param [ids as int]
	"""
	def set_playlist(self, new_playlist):
		self._playlist = new_playlist
		self.emit("playlist-changed")
	"""
		Return playlist
		@return [ids as int]
	"""
	def get_playlist(self):
		return self._playlist

	"""
		True if track_id exist in playlist
		@param track id as int
		@return bool
	"""
	def is_in_playlist(self, track_id):
		return track_id in self._playlist

	"""
		Return track position in playlist
		@param track id as int
		@return position as int
	"""
	def get_track_position(self, track_id):
		return self._playlist.index(track_id)

#######################
# PRIVATE             #
#######################

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
		a fresh sqlite cursor should be pass as sql if we are in a thread
		@param bool, sqlite cursor
	"""
	def _shuffle_next(self, force = False, sql = None):
		track_id = self._get_random(sql)
		self._current_track_album_id = Objects["tracks"].get_album_id(track_id, sql)
		# Need to clear history
		if not track_id:
			self._albums = self._shuffle_albums_history
			self._shuffle_tracks_history = []
			self._shuffle_albums_history = []
			self._shuffle_next()
			return

		if force:
			self.load(track_id)
		else:
			self._load_track(track_id, sql)


	"""
		Return a random track and make sure it has never been played
		@param sqlite cursor
	"""
	def _get_random(self, sql = None):
		for album in sorted(self._albums, key=lambda *args: random.random()):
			if not album in self._shuffle_albums_history:
				tracks = Objects["albums"].get_tracks(album, sql)
				for track in sorted(tracks, key=lambda *args: random.random()):
					if not track in self._shuffle_tracks_history:
						return track
			# No new tracks for this album, remove it
			self._albums.remove(album)
			self._shuffle_albums_history.append(album)
		return None

	"""
		On stream start
		Emit "current-changed" to notify others components
		Add track to shuffle history if needed
	"""
	def _on_stream_start(self, bus, message):
		self.emit("current-changed", self._current_track_id)
		self._duration = Objects["tracks"].get_length(self._current_track_id)
		if self._shuffle or self._party:
			self._shuffle_tracks_history.append(self._current_track_id)

	"""
		On error, next()
	"""
	def _on_bus_error(self, bus, message):
		self.next()
		
	"""
		On eos, force loading if queue fails,
		if on_stream_about_to_finish never get send  
	"""
	def _on_bus_eos(self, bus, message):
		self.load(self._current_track_id)
		

	"""
		When stream is about to finish, switch to next track without gap
	"""
	def _on_stream_about_to_finish(self, obj):
		self._previous_track_id = self._current_track_id
		# We are in a thread, we need to create a new cursor
		sql = Objects["db"].get_cursor()
		self.next(False, sql)
		# Add populariy if we listen to the song
		album_id = Objects["tracks"].get_album_id(self._previous_track_id, sql)
		Objects["albums"].set_more_popular(album_id, sql)

		sql.close()

	"""
		Call progress callback with new position
	"""
	def _update_position(self):
		position = self._playbin.query_position(Gst.Format.TIME)[1] / 1000000000

		if position > 0:
			self.emit("position-changed", position*60)
		return True
		
	"""
		Load track
		@param track id as int, sqlite cursor
	"""
	def _load_track(self, track_id, sql = None):
		filepath = Objects["tracks"].get_path(track_id, sql)
		if path.exists(filepath):
			self._current_track_id = track_id
			self._playbin.set_property('uri', "file://" + filepath)
