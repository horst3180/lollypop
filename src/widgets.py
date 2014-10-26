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
# Many code inspiration from gnome-music at the GNOME project

from gi.repository import Gtk, Gdk, GLib, GObject, Pango
from gi.repository import GdkPixbuf
from cgi import escape
from gettext import gettext as _

from lollypop.config import *
from lollypop.albumart import AlbumArt
from lollypop.player import Player
from lollypop.popimages import PopImages
from lollypop.utils import translate_artist_name

class AlbumWidget(Gtk.Grid):

	"""
		Init album widget ui with an vertical grid:
			- Album cover
			- Album name
			- Artist name
	"""
	def __init__(self, album_id):
		Gtk.Grid.__init__(self)
		self._ui = Gtk.Builder()
		self._ui.add_from_resource('/org/gnome/Lollypop/AlbumWidget.ui')
		
		self._album_id = album_id
		
		self._cover = self._ui.get_object('cover')
		self._cover.set_from_pixbuf(Objects["art"].get(album_id, ART_SIZE_BIG))

		album_name = Objects["albums"].get_name(album_id)
		title = self._ui.get_object('title')
		title.set_max_width_chars(20)
		title.set_label(album_name)
		artist_name = Objects["albums"].get_artist_name(album_id)
		artist_name = translate_artist_name(artist_name)
		artist = self._ui.get_object('artist')
		artist.set_max_width_chars(20)
		artist.set_label(artist_name)
		
		layout = title.get_layout()
		print(layout.get_pixel_size())

		self.add(self._ui.get_object('AlbumWidget'))
	
	"""
		Update cover for album id
	"""
	def update_cover(self, album_id):
		if self._album_id == album_id:
			self._cover.set_from_pixbuf(Objects["art"].get(album_id, ART_SIZE_BIG))

	"""
		Return album id for widget
	"""     
	def get_id(self):
		return self._album_id


class AlbumWidgetSongs(Gtk.Grid):

	"""
		Init album widget songs ui with a complex grid:
			- Album cover
			- Album name
			- Albums tracks aligned on two columns
	"""
	def __init__(self, album_id, genre_id):
		Gtk.Grid.__init__(self)
		self._ui = Gtk.Builder()
		self._ui.add_from_resource('/org/gnome/Lollypop/AlbumWidgetSongs.ui')
		
		self._tracks_ui = []
		self._tracks = []
		self._artist_id = Objects["artists"].get_id(album_id)
		self._album_id = album_id
		self._genre_id = genre_id

		self.set_vexpand(False)
		self.set_hexpand(False)
		grid = self._ui.get_object('grid2')

		self._nb_tracks = Objects["albums"].get_count(album_id)
		self._cover = self._ui.get_object('cover')
		self._cover.set_from_pixbuf(Objects["art"].get(album_id, ART_SIZE_BIG))
		self._ui.get_object('title').set_label(Objects["albums"].get_name(album_id))
		self._ui.get_object('year').set_label(Objects["albums"].get_year(album_id))
		self.add(self._ui.get_object('AlbumWidgetSongs'))

		self._eventbox = self._ui.get_object('eventbox')
		self._eventbox.connect("button-press-event", self._show_web_art)

		Objects["player"].connect("playlist-changed", self._update_pos_labels)

		self._add_tracks(album_id)
	
	def destroy(self):
		for ui in self._tracks_ui:
			for obj in ui.get_objects():
				obj.destroy()
		for obj in self._ui.get_objects():
			obj.destroy()
		Gtk.Grid.destroy(self)

	"""
		Update tracks settings current tracks as bold and adding play symbol
	"""
	def update_tracks(self, track_id):
		for track_widget in self._tracks:
			# Update position label
			self._update_pos_label(track_widget)
			
			track_name = Objects["tracks"].get_name(track_widget.id)
			# If we are listening to a compilation, prepend artist name
			if self._artist_id == -1:
				artist_name = translate_artist_name(Objects["tracks"].get_artist_name(track_id))
				track_name =  artist_name + " - " + track_name

			# Update playing label
			if track_widget.id == track_id:
				track_widget.title.set_markup('<b>%s</b>' % escape(track_name))
				track_widget.playing.show()
			else:
				if track_widget.playing.is_visible():
					track_widget.playing.hide()
					track_widget.title.set_text(track_name)


	"""
		Update cover for album id
	"""
	def update_cover(self, album_id):
		if self._album_id == album_id:
			self._cover.set_from_pixbuf(Objects["art"].get(album_id, ART_SIZE_BIG))
	
	"""
		Return album id for widget
	"""     
	def get_id(self):
		return self._album_id
			
#######################
# PRIVATE             #
#######################

	"""
		Add tracks for album_id to Album widget
	"""
	def _add_tracks(self, album_id):
		i = 0

		for track_id, name, filepath, length in Objects["albums"].get_tracks_infos(album_id):
			# If we are listening to a compilation, prepend artist name
			if self._artist_id == -1:
				artist_name = translate_artist_name(Objects["tracks"].get_artist_name(track_id))
				name =  artist_name + " - " + name
			ui = Gtk.Builder()
			self._tracks_ui.append(ui)
			ui.add_from_resource('/org/gnome/Lollypop/TrackWidget.ui')
			track_widget = ui.get_object('eventbox1')
			self._tracks.append(track_widget)
			track_widget.playing = ui.get_object('image1')
			track_widget.playing.set_alignment(1, 0.6)
			
			track_widget.connect("button-release-event", self._track_selected)

			ui.get_object('num').set_markup('<span color=\'grey\'>%d</span>' % len(self._tracks))
			track_widget.title = ui.get_object('title')
			track_widget.id = track_id
			if not track_id == Objects["player"].get_current_track_id():
				track_widget.playing.set_no_show_all('True')
				track_widget.title.set_text(name)
			else:
				track_widget.title.set_markup('<b>%s</b>' % escape(name))

			ui.get_object('title').set_alignment(0.0, 0.5)
			self._ui.get_object('grid2').attach(track_widget,
                    					   int(i / (self._nb_tracks / 2)),
                    					   int(i % (self._nb_tracks / 2)), 1, 1
                					   )
			ui.get_object('duration').set_text(Objects["player"].seconds_to_string(length))
			track_widget.play_pos = ui.get_object('play-pos')
			self._update_pos_label(track_widget)
			track_widget.show_all()
			i += 1
	
	"""
		On track selected, emit "new-playlist" with track_id as arg
	"""		
	def _track_selected(self, widget, event):
		# Left click => Play
		if event.button == 1:
			for track_widget in self._tracks:
				if track_widget == widget:
					Objects["player"].load(widget.id)
					if not Objects["player"].is_party():
						Objects["player"].set_albums(None, self._genre_id, widget.id)
		# Add/Remove to/from playlist		
		else:
			if Objects["player"].is_in_playlist(widget.id):
				Objects["player"].del_from_playlist(widget.id)
			else:
				Objects["player"].add_to_playlist(widget.id)
			self._update_pos_labels()

	"""
		Update all position labels
	"""
	def _update_pos_labels(self, obj = None):
		for track_widget in self._tracks:
			self._update_pos_label(track_widget)

	"""
		Update postion label for track widget
	"""
	def _update_pos_label(self, track_widget):
		if Objects["player"].is_in_playlist(track_widget.id):
			pos = Objects["player"].get_track_position(track_widget.id) + 1
			track_widget.play_pos.set_text(str(pos))
		else:
			track_widget.play_pos.set_text("")

	"""
		Popover with album art downloaded from the web (in fact google :-/)
	"""
	def _show_web_art(self, obj, data):
		artist = Objects["artists"].get_name(self._artist_id)
		album = Objects["albums"].get_name(self._album_id)
		urls = Objects["art"].get_google_arts(artist + " " + album)
		popover = PopImages(self._album_id)
		popover.set_relative_to(obj)
		popover.set_urls(urls)
		popover.populate()
		popover.show()

	
	
