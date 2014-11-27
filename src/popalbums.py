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

from lollypop.view import ArtistView
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
		
		self._size_group = Gtk.SizeGroup(mode=Gtk.SizeGroupMode.HORIZONTAL)

		self._stack = Gtk.Stack()
		self._stack.set_transition_duration(500)
		self._stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT)
		self._stack.show()
		self.add(self._stack)
		
		Objects["player"].connect("current-changed", self._update_content)
		self.update_view_class(Objects["settings"].get_value('dark-view'))

	"""
		Run _populate in a thread
	"""
	def populate(self, track_id):
		artist_id = Objects["tracks"].get_performer_id(track_id)
		if artist_id == -1:
			artist_id = Objects["tracks"].get_artist_id(track_id)
		view = ArtistView(artist_id, None, True)
		view.connect('finished', self._switch_view)
		view.populate()
		self._stack.add(view)
		view.show()

	"""
		Resize popover and set signals callback
	"""
	def do_show(self):
		width, height = get_monitor_size()
		self.set_property('height-request', height*0.8)
		self.set_property('width-request', width*0.65)
		Gtk.Popover.do_show(self)
	
	"""
		Reset artist id and clean signals callback
	"""
	def do_hide(self):
		self._artist_id = None
		Gtk.Popover.do_hide(self)
		
	"""
		Update view class
		@param bool
	"""
	def update_view_class(self, dark):
		if dark:
			self._stack.get_style_context().add_class('black')
		else:
			self._stack.get_style_context().remove_class('black')

#######################
# PRIVATE             #
#######################

	"""
		Switch to view
		@param view as ArtistView
	"""
	def _switch_view(self, view):
		previous = self._stack.get_visible_child()
		# On first load, view == previous
		if view != previous:
			self._stack.set_visible_child(view)
			if previous:
				self._stack.remove(previous)

	"""
		Update the content view
		@param player as Player
		@param track id as int
	"""
	def _update_content(self, player, track_id):
		if self.is_visible():
			self.populate(track_id)
	
