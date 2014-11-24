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

from gettext import gettext as _, ngettext 
from gi.repository import Gtk, GLib, Gio, GdkPixbuf
from _thread import start_new_thread
from time import sleep

from lollypop.widgets import ArtistWidget
from lollypop.config import *
from lollypop.utils import get_monitor_size

class PopAlbums(Gtk.Popover):

	"""
		Init Popover ui with a text entry and a scrolled treeview
	"""
	def __init__(self):
		Gtk.Popover.__init__(self)

		self._widgets = []
		self._populating_view = None
		self._artist_id = None

		self._stack = Gtk.Stack()
		self._stack.set_transition_duration(500)
		self._stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT)
		self._stack.show()
		
		self._scroll = Gtk.ScrolledWindow()
		self._scroll.set_hexpand(True)
		self._scroll.set_vexpand(True)
		self._scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
		self._scroll.add(self._stack)
		self._scroll.show()

		self.add(self._scroll)	

	"""
		Run _populate in a thread
	"""
	def populate(self, track_id):
		artist_id = Objects["tracks"].get_performer_id(track_id)
		if artist_id == -1:
			artist_id = Objects["tracks"].get_artist_id(track_id)
		if self._artist_id == artist_id:
			for widget in self._widgets:
				widget.update_playing_track(track_id)
		else:
			self._widget = []
			self._artist_id = artist_id
			
			view = self._get_new_view()
			self._stack.add(view)
			if not self._populating_view:
				self._stack.set_visible_child(view)
			self._populating_view = view
			start_new_thread(self._populate, (view , artist_id, track_id))

	"""
		Resize popover and set signals callback
	"""
	def do_show(self):
		width, height = get_monitor_size()
		self.set_property('height-request', height*0.8)
		self.set_property('width-request', width*0.65)
		Objects["player"].connect("current-changed", self._update_content)
		Gtk.Popover.do_show(self)
	
	"""
		Reset artist id and clean signals callback
	"""
	def do_hide(self):
		self._artist_id = None
		Objects["player"].disconnect_by_func(self._update_content)
		Gtk.Popover.do_hide(self)
		for child in self._stack.get_children():
			GLib.idle_add(self._remove_child, child, priority=GLib.PRIORITY_LOW)

#######################
# PRIVATE             #
#######################

	"""
		Populate view
		@param view, artist id as int, track_id as int
	"""
	def _populate(self, view, artist_id, track_id):
		sql = Objects["db"].get_cursor()
		albums = Objects["artists"].get_albums(artist_id, sql)
		GLib.idle_add(self._add_albums, view, albums)

	"""
		Remove view
		@param view
	"""
	def _remove_unused_views(self, view):
		if view == self._populating_view:
			for child in self._stack.get_children():
				if child != view:
					self._stack.remove(child)

	"""
		Get a new view
	"""
	def _get_new_view(self):
		view = Gtk.Grid()
		view.set_orientation(Gtk.Orientation.VERTICAL)
		view.set_column_spacing(20)
		view.set_row_spacing(20)
		view.show()
		if Objects["settings"].get_value('dark-view'):
			view.get_style_context().add_class('black')
		return view

	"""
		Clean the view
	"""
	def _remove_child(self, child):
		self._stack.remove(child)

	"""
		Switch to no visible view
	"""
	def _switch_view(self, view):
		self._stack.set_visible_child(view)
		GLib.timeout_add(500, self._remove_unused_views, view)

	"""
		Pop an album and add it to the view,
		repeat operation until album list is empty
		@param view, [album ids as int]
	"""
	def _add_albums(self, view, albums):
		if self._populating_view != view:
			return
		elif len(albums) > 0:
			album_id = albums.pop(0)
			genre_id = Objects["albums"].get_genre(album_id)
			widget = ArtistWidget(album_id, genre_id)
			self._widgets.append(widget)
			widget.show()
			view.add(widget)
			GLib.idle_add(self._add_albums, view, albums, priority=GLib.PRIORITY_LOW)
		else:
			GLib.idle_add(self._switch_view, view)

	"""
		Update the content view
	"""
	def _update_content(self, obj, track_id):
		if self.is_visible():
			self.populate(track_id)
	
