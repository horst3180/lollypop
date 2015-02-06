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

from gi.repository import Gtk, Gdk, GLib, GObject, Pango
from gi.repository import GdkPixbuf
from gettext import gettext as _

from cgi import escape

from lollypop.define import *
from lollypop.tracks import TracksWidget
from lollypop.albumart import AlbumArt
from lollypop.player import Player
from lollypop.popmenu import PopMainMenu
from lollypop.playlists import PlaylistEditPopup
from lollypop.popimages import PopImages
from lollypop.utils import translate_artist_name

"""
	Album widget is a pixbuf with two labels: albumm name and artist name
"""
class AlbumWidget(Gtk.Grid):

	"""
		Init album widget ui with an vertical grid:
			- Album cover
			- Album name
			- Artist name
	"""
	def __init__(self, album_id):
		Gtk.Grid.__init__(self)
		self._album_id = album_id

		self.set_property("margin", 5)

		self.set_orientation(Gtk.Orientation.VERTICAL)
		self._ui = Gtk.Builder()
		self._ui.add_from_resource('/org/gnome/Lollypop/AlbumWidget.ui')
		
		self._cover = self._ui.get_object('cover')
		self._cover.set_from_pixbuf(Objects.art.get(album_id, ART_SIZE_BIG))

		album_name = Objects.albums.get_name(album_id)
		title = self._ui.get_object('title')	
		title.set_label(album_name)
		artist_name = Objects.albums.get_artist_name(album_id)
		artist_name = translate_artist_name(artist_name)
		artist = self._ui.get_object('artist')
		artist.set_label(artist_name)

		self.add(self._cover)
		self.add(title)
		self.add(artist)
	
	def do_get_preferred_width(self):
		return (ART_SIZE_BIG, ART_SIZE_BIG)
		
	"""
		Update cover for album id
		@param album id as int
	"""
	def update_cover(self, album_id):
		if self._album_id == album_id:
			self._cover.set_from_pixbuf(Objects.art.get(album_id, ART_SIZE_BIG))

	"""
		Return album id for widget
		@return album id as int
	"""     
	def get_id(self):
		return self._album_id


"""
	Album detailed Widget is a pixbuf with album name and tracks list
"""
class AlbumDetailedWidget(Gtk.Grid):

	"""
		Init album widget songs ui with a complex grid:
			- Album cover
			- Album name
			- Albums tracks aligned on two columns
		if cover_add True, let user change album cover
		@param album id as int
		@param genre id as int
		@param parent width as int
		@param limit_to_artist as bool to load artist albums on play
		@param show_menu as bool if menu need to be displayed
		@param size group as Gtk.SizeGroup
	"""
	def __init__(self, album_id, genre_id, limit_to_artist, show_menu, size_group):
		Gtk.Grid.__init__(self)
		self.set_property("margin", 5)

		self._ui = Gtk.Builder()
		self._ui.add_from_resource('/org/gnome/Lollypop/AlbumDetailedWidget.ui')
		
		self._artist_id = Objects.albums.get_artist_id(album_id)
		self._album_id = album_id
		self._genre_id = genre_id
		self._limit_to_artist = limit_to_artist

		self._tracks_widget1 = TracksWidget(show_menu)
		self._tracks_widget2 = TracksWidget(show_menu)
		size_group.add_widget(self._tracks_widget1)
		size_group.add_widget(self._tracks_widget2)
		self._tracks_widget1.connect('activated', self._on_activated)
		self._tracks_widget2.connect('activated', self._on_activated)
		self._ui.get_object('tracks').add(self._tracks_widget1)
		self._ui.get_object('tracks').add(self._tracks_widget2)
		self._tracks_widget1.show()
		self._tracks_widget2.show()

		self._cover = self._ui.get_object('cover')
		self._cover.set_from_pixbuf(Objects.art.get(album_id, ART_SIZE_BIG))
		self._ui.get_object('title').set_label(Objects.albums.get_name(album_id))
		self._ui.get_object('year').set_label(Objects.albums.get_year(album_id))
		self.add(self._ui.get_object('AlbumDetailedWidget'))

		if show_menu:
			self.eventbox = self._ui.get_object('eventbox')
			self.eventbox.connect("button-press-event", self._show_web_art)
			self._ui.get_object('menu').connect('clicked', self._pop_menu, album_id)
			self._ui.get_object('menu').show()
		else:
			self.eventbox = None
		self._add_tracks(album_id)

	"""
		Update playing track
		@param track id as int
	"""
	def update_playing_track(self, track_id):
		self._tracks_widget1.update_playing(track_id)	
		self._tracks_widget2.update_playing(track_id)

	"""
		Update cover for album id
		@param album id as int
	"""
	def update_cover(self, album_id):
		if self._album_id == album_id:
			self._cover.set_from_pixbuf(Objects.art.get(album_id, ART_SIZE_BIG))
	
	"""
		Return album id for widget
		@return album id as int
	"""     
	def get_id(self):
		return self._album_id

#######################
# PRIVATE             #
#######################

	"""
		Popup menu for album
		@param widget as Gtk.Button
		@param album id as int
	"""
	def _pop_menu(self, widget, album_id):
		menu = PopMainMenu(album_id, True)
		popover = Gtk.Popover.new_from_model(self._ui.get_object('menu'), menu)
		popover.show()

	"""
		Add tracks for album_id to Album widget
		@param album id as int
	"""
	def _add_tracks(self, album_id):
		i = 1    					   
		mid_tracks = int(0.5+Objects.albums.get_count(album_id)/2)
		for track_id, title, artist_id, filepath, length in Objects.albums.get_tracks_infos(album_id):
		
			# If we are listening to a compilation, prepend artist name
			if self._artist_id == COMPILATIONS or self._artist_id != artist_id:
				artist_name = translate_artist_name(Objects.tracks.get_artist_name(track_id))
				title =  artist_name + " - " + title
				
			# Get track position in queue
			pos = None
			if Objects.player.is_in_queue(track_id):
				pos = Objects.player.get_track_position(track_id)
				
			if i <= mid_tracks:
				self._tracks_widget1.add_track(track_id, i, escape(title), length, pos) 
			else:
				self._tracks_widget2.add_track(track_id, i, escape(title), length, pos) 
			i += 1
	
	"""
		On track activation, play track
		@param widget as TracksWidget
		@param track id as int
	"""		
	def _on_activated(self, widget, track_id):
		if not Objects.player.is_party():
			Objects.player.set_albums(self._artist_id, self._genre_id, self._limit_to_artist)
		Objects.player.load(track_id)

	"""
		Popover with album art downloaded from the web (in fact google :-/)
		@param: widget as eventbox
		@param: data as unused
	"""
	def _show_web_art(self, widget, data):
		artist = Objects.artists.get_name(self._artist_id)
		album = Objects.albums.get_name(self._album_id)
		popover = PopImages(self._album_id)
		popover.set_relative_to(widget)
		popover.populate(artist + " " + album)
		popover.show()


"""
	Playlist Widget is similar to album detailed widget but show a cover grid as playlist cover
"""
class PlaylistWidget(Gtk.Grid):
	"""
		Init playlist Widget
		@param playlist name as str
	"""
	def __init__(self, playlist_name):
		Gtk.Grid.__init__(self)
		self.set_property("margin", 5)
		self._is_loaded = False
		self._ui = Gtk.Builder()
		self._ui.add_from_resource('/org/gnome/Lollypop/PlaylistWidget.ui')

		self._tracks_widget1 = TracksWidget(False)
		self._tracks_widget2 = TracksWidget(False)
		self._tracks_widget1.connect('activated', self._on_activated, playlist_name)
		self._tracks_widget2.connect('activated', self._on_activated, playlist_name)
		self._tracks_widget1.show()
		self._tracks_widget2.show()

		size_group = Gtk.SizeGroup(mode=Gtk.SizeGroupMode.HORIZONTAL)
		size_group.add_widget(self._tracks_widget1)
		size_group.add_widget(self._tracks_widget2)

		self._ui.get_object('menu').connect('clicked', self._pop_menu, playlist_name)
		self._ui.get_object('tracks').add(self._tracks_widget1)
		self._ui.get_object('tracks').add(self._tracks_widget2)

		self._header = self._ui.get_object('header')
		
		self._ui.get_object('title').set_label(playlist_name)
		self.add(self._ui.get_object('PlaylistWidget'))

	"""
		Populate list one
		@param track's ids as array of int
		@param track position as int
	"""
	def populate_list_one(self, tracks, pos):
		self._add_tracks(tracks, self._tracks_widget1, pos)
		
	"""
		Populate list two
		@param track's ids as array of int
		@param track position as int
	"""
	def populate_list_two(self, tracks, pos):
		self._add_tracks(tracks, self._tracks_widget2, pos)

	"""
		Update playing track
		@param track id as int
	"""
	def update_playing_track(self, track_id):
		self._tracks_widget1.update_playing(track_id)	
		self._tracks_widget2.update_playing(track_id)


	"""
		Clear tracks
	"""
	def clear(self):
		for child in self._tracks_widget1.get_children():
			child.destroy()
		for child in self._tracks_widget2.get_children():
			child.destroy()

#######################
# PRIVATE             #
#######################
	"""
		Add tracks to list
		@param tracks id as array of [int]
		@param widget TracksWidget
		@param track position as int
	"""
	def _add_tracks(self, tracks, widget, pos):
		if len(tracks) == 0:
			return
		track_id = tracks.pop(0)
		(title, filepath, length, artist_id, album_id) = Objects.tracks.get_infos(track_id)
		title = "<b>%s</b>\n %s" % (escape(translate_artist_name(Objects.artists.get_name(artist_id))), escape(title))

		widget.add_track(track_id, pos, title, length, None, True)
		GLib.idle_add(self._add_tracks, tracks, widget, pos+1)

	"""
		Popup menu for playlist
		@param widget as Gtk.Button
		@param playlist name as str
	"""
	def _pop_menu(self, widget, playlist_name):
		popup = PlaylistEditPopup(playlist_name)
		popup.show()

	"""
		On track activation, play track
		@param widget as TracksWidget
		@param track id as int
		@param playlist name as str
	"""		
	def _on_activated(self, widget, track_id, playlist_name):
		if not Objects.player.is_party() and not self._is_loaded:
			tracks = Objects.playlists.get_tracks_id(playlist_name)
			Objects.player.set_user_playlist(tracks, track_id)
			self._is_loaded = True
		Objects.player.load(track_id)
