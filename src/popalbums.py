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

from gettext import gettext as _, ngettext 
from gi.repository import Gtk, GLib, Gio, GdkPixbuf
from _thread import start_new_thread
from time import sleep

from lollypop.widgets import AlbumWidgetSongs
from lollypop.config import *
from lollypop.utils import get_monitor_size

class PopAlbums(Gtk.Popover):

	"""
		Init Popover ui with a text entry and a scrolled treeview
	"""
	def __init__(self):
		Gtk.Popover.__init__(self)

		self._widgets = []

		self._artist_id = None

		Objects["player"].connect("current-changed", self._update_content)
		self.connect('closed', self._on_closed)

		self._stack = Gtk.Stack()
		self._stack.set_transition_duration(500)
		self._stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
		self._stack.show()
		
		self._add_new_view()
		
		self._scroll = Gtk.ScrolledWindow()
		self._scroll.set_hexpand(True)
		self._scroll.set_vexpand(True)
		self._scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
		self._scroll.add(self._stack)
		self._scroll.show()

		self.add(self._scroll)	

	"""
		Populate view, can be threaded
		arg: artist id as int
	"""
	def populate(self, artist_id):
		sql = Objects["db"].get_cursor()
		self._artist_id = artist_id
		albums = Objects["artists"].get_albums(artist_id, sql)
		GLib.idle_add(self._add_albums, albums)

	"""
		Resize popover
	"""
	def do_show(self):
		width, height = get_monitor_size()
		self.set_property('height-request', height*0.8)
		self.set_property('width-request', width*0.65)
		Gtk.Popover.do_show(self)

#######################
# PRIVATE             #
#######################

	"""
		Add a new view to stack
	"""
	def _add_new_view(self):
		self._view = Gtk.Grid()
		self._view.set_orientation(Gtk.Orientation.VERTICAL)
		self._view.set_column_spacing(20)
		self._view.set_row_spacing(20)
		self._view.show()
		self._view.get_style_context().add_class('black')
		self._stack.add(self._view)

	"""
		On closed, clean stack and add a new fresh view
	"""
	def _on_closed(self, widget):
		for child in self._stack.get_children():
			GLib.idle_add(self._remove_child, child, priority=GLib.PRIORITY_LOW)
		self._add_new_view()

	"""
		Clean the views and 
	"""
	def _remove_child(self, child):
		self._stack.remove(child)

	"""
		Switch to no visible view
	"""
	def _switch_view(self):
		previous = self._stack.get_visible_child()
		self._stack.set_visible_child(self._view)
		if previous != self._view:
			self._stack.remove(previous)

	"""
		Pop an album and add it to the view,
		repeat operation until album list is empty
		arg: [album ids as int]
	"""
	def _add_albums(self, albums):
		if len(albums) > 0:
			album_id = albums.pop(0)
			genre_id = Objects["albums"].get_genre(album_id)
			widget = AlbumWidgetSongs(album_id, genre_id)
			widget.show()
			self._view.add(widget)
			GLib.idle_add(self._add_albums, albums, priority=GLib.PRIORITY_LOW)
		else:
			GLib.idle_add(self._switch_view)

	"""
		Update the content view
	"""
	def _update_content(self, obj, data):
		if self.is_visible():
			track_id = Objects["player"].get_current_track_id()
			artist_id = Objects["tracks"].get_artist_id(track_id)
			if artist_id != self._artist_id:
				self._add_new_view()
				self._widgets = []
				start_new_thread(self.populate, (artist_id, ))
			else:
				for widget in self._widgets:
					widget.update_tracks(track_id)
	
