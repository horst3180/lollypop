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

from time import sleep
from gettext import gettext as _, ngettext 
from gi.repository import Gtk, GLib, Gio, GdkPixbuf

from lollypop.widgets import AlbumWidgetSongs
from lollypop.config import *

class PopAlbums(Gtk.Popover):

	"""
		Init Popover ui with a text entry and a scrolled treeview
	"""
	def __init__(self):
		Gtk.Popover.__init__(self)

		self._widgets = []

		self._artist_id = None

		self._view = Gtk.FlowBox()
		self._view.set_column_spacing(20)
		self._view.set_row_spacing(20)
		self._view.set_selection_mode(Gtk.SelectionMode.NONE)
		self._view.connect("child-activated", self._on_activate)
		self._view.show()
		self._view.get_style_context().add_class('black')

		self._scroll = Gtk.ScrolledWindow()
		self._scroll.set_hexpand(True)
		self._scroll.set_vexpand(True)
		self._scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
		self._scroll.add(self._view)
		self._scroll.show()

		self.set_property('height-request', 700)
		self.set_property('width-request', 1000)

		self.add(self._scroll)	

	"""
		Populate view
	"""
	def populate(self, artist_id):
		self._artist_id = artist_id
		for child in self._view.get_children():
			child.destroy()
		Objects["player"].connect("current-changed", self._update_content)
		albums = Objects["artists"].get_albums(artist_id)
		for album_id in albums:
			genre_id = Objects["albums"].get_genre(album_id)
			widget = AlbumWidgetSongs(album_id, genre_id)
			widget.show()
			self._widgets.append(widget)
			self._view.insert(widget, -1)
		
	
#######################
# PRIVATE             #
#######################		
	"""
		Update the content view
	"""
	def _update_content(self, obj, data):
		track_id = Objects["player"].get_current_track_id()
		artist_id = Objects["tracks"].get_artist_id(track_id)
		if artist_id != self._artist_id:
			self.populate(artist_id)
		else:
			for widget in self._widgets:
				widget.update_tracks(track_id)
	
	"""
		hide
	"""
	def _on_activate(self, flowbox, child):
		Objects["player"].disconnect_by_func(self._update_content)
		self._widgets = []
		self.hide()
		
		
