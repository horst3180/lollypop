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
from lollypop.define import *

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
		self._stack.set_transition_duration(1000)
		self._stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
		self._stack.show()
		self.add(self._stack)
		
		Objects.player.connect("current-changed", self._update_content)

	"""
		Run _populate in a thread
	"""
	def populate(self, track_id):
		artist_id = Objects.tracks.get_performer_id(track_id)
		if artist_id == -1:
			artist_id = Objects.tracks.get_artist_id(track_id)
		if self._artist_id == artist_id:
			return

		view = ArtistView(artist_id, None, True)
		self._stack.add(view)
		if self._artist_id:
				view.connect('finished', self._switch_view)
				# Destroy hidden view, which are in populate() thread
				for child in self._stack.get_children():
					if child != view and self._stack.get_visible_child() != child:
						child.destroy()
		else:
			self._switch_view(view)
		start_new_thread(view.populate, ())
		self._artist_id = artist_id
		view.show()

	"""
		Resize popover and set signals callback
	"""
	def do_show(self):
		size_setting = Objects.settings.get_value('window-size')
		if isinstance(size_setting[0], int) and isinstance(size_setting[1], int):
			self.set_property('width-request', size_setting[0]*0.65)
			self.set_property('height-request', size_setting[1]*0.8)
		else:
			self.set_property('width-request', 600)
			self.set_property('height-request', 600)
		Gtk.Popover.do_show(self)

#######################
# PRIVATE             #
#######################

	"""
		Switch to view
		@param view as ArtistView
	"""
	def _switch_view(self, view):
		previous = self._stack.get_visible_child()
		self._stack.set_visible_child(view)
		if previous and previous != view:
			previous.destroy()

	"""
		Update the content view
		@param player as Player
		@param track id as int
	"""
	def _update_content(self, player, track_id):
		if self.is_visible():
			self.populate(track_id)
		else:
			artist_id = Objects.tracks.get_performer_id(track_id)
			if artist_id == -1:
				artist_id = Objects.tracks.get_artist_id(track_id)
			if self._artist_id != artist_id:
				self._artist_id = None
				current = self._stack.get_visible_child()
				if current:
					current.destroy()
	
