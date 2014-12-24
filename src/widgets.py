#!/usr/bin/python
# Copyright (c) 2014 Cedric Bellegarde <gnumdk@gmail.com>
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

from lollypop.define import *
from lollypop.tracks import TracksWidget
from lollypop.albumart import AlbumArt
from lollypop.player import Player
from lollypop.popmenu import PopMenu
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
	Artist Widget is a pixbuf with album name and tracks list
"""
class ArtistWidget(Gtk.Grid):

	"""
		Init album widget songs ui with a complex grid:
			- Album cover
			- Album name
			- Albums tracks aligned on two columns
		if cover_add True, let user change album cover
		@param album id as int
		@param genre id as int
		@param parent width as int
		@param full as bool => Full playlist should be loaded
		@param popover authorized as bool
		@param size group as Gtk.SizeGroup
	"""
	def __init__(self, album_id, genre_id, full, popover, size_group):
		Gtk.Grid.__init__(self)
		self._ui = Gtk.Builder()
		self._ui.add_from_resource('/org/gnome/Lollypop/ArtistWidget.ui')
		
		self._artist_id = Objects.albums.get_artist_id(album_id)
		self._album_id = album_id
		self._genre_id = genre_id
		self._full = full

		self._tracks_widget1 = TracksWidget(popover)
		self._tracks_widget2 = TracksWidget(popover)
		if size_group:
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
		self.add(self._ui.get_object('ArtistWidget'))

		if popover:
			self._eventbox = self._ui.get_object('eventbox')
			self._eventbox.connect("button-press-event", self._show_web_art)
			self._ui.get_object('menu').connect('clicked', self._pop_menu, album_id)
			self._ui.get_object('menu').show()

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
		menu = PopMenu(album_id, True)
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
				self._tracks_widget1.add_track(track_id, i, title, length, pos) 
			else:
				self._tracks_widget2.add_track(track_id, i, title, length, pos) 
			i += 1
	
	"""
		On track activation, play track
		@param widget as TracksWidget
		@param track id as int
	"""		
	def _on_activated(self, widget, track_id):
		Objects.player.load(track_id)
		if not Objects.player.is_party():
			Objects.player.set_albums(self._artist_id, self._genre_id, self._full)

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
	Widget used to let user select a collection folder
"""
class ChooserWidget(Gtk.Grid):
	
	def __init__(self):
		Gtk.Grid.__init__(self)
		self._action = None
		self.set_property("orientation", Gtk.Orientation.HORIZONTAL)
		self.set_property("halign", Gtk.Align.CENTER)
		self._chooser_btn = Gtk.FileChooserButton()
		self._chooser_btn.set_action(Gtk.FileChooserAction.SELECT_FOLDER)
		self._chooser_btn.set_property("margin", 5)
		self._chooser_btn.show()
		self.add(self._chooser_btn)
		self._action_btn = Gtk.Button(None)
		self._action_btn.set_property("margin", 5)
		self._action_btn.show()
		self.add(self._action_btn)
		self._action_btn.connect("clicked", self._do_action)
		self.show()
	
	"""
		Set current selected path for chooser
		@param directory path as string
	"""
	def set_dir(self, path):
		if path:
			self._chooser_btn.set_uri("file://"+path)
	
	"""
		Set image for action button
		@param Gtk.Image
	"""
	def set_icon(self, image):
		self._action_btn.set_image(image)
		
	"""
		Set action callback for button clicked signal
		@param func
	"""
	def set_action(self, action):
		self._action = action

	"""
		Return select directory path
		@return path as string
	"""
	def get_dir(self):
		path =  GLib.uri_unescape_string(self._chooser_btn.get_uri(), None)
		if path:
			return path[7:]
		else:
			return None
		
#######################
# PRIVATE             #
#######################
	"""
		If action defined, execute, else, remove widget
	"""
	def _do_action(self, widget):
		if self._action:
			self._action()
		else:
			self.destroy()
