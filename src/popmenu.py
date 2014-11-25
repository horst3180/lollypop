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

from gettext import gettext as _
from gi.repository import Gtk, GObject, GLib, Gio
import urllib.request
import urllib.parse
from _thread import start_new_thread

from lollypop.config import *

class PopMenu(Gio.Menu):
	"""
		Init menu model
		@param: object id as int
		@param: is album as bool
	"""
	def __init__(self, object_id, is_album):
		Gio.Menu.__init__(self)
		self._is_album = is_album
		app = Gio.Application.get_default()

		append_wait_list_action = Gio.SimpleAction(name="append_wait_list_action")
		app.add_action(append_wait_list_action)
		prepend_wait_list_action = Gio.SimpleAction(name="prepend_wait_list_action")
		app.add_action(prepend_wait_list_action)
		del_wait_list_action = Gio.SimpleAction(name="del_wait_list_action")
		app.add_action(del_wait_list_action)
		waitlist = Objects["player"].get_waitlist()
		append = True
		prepend = True
		delete = True
		if len(waitlist) == 0:
			append = False
		if not is_album:
			if object_id in waitlist:
				if len(waitlist) > 0 and waitlist[0] == object_id:
					prepend = False
				append = False
			else:
				delete = False
		else:
			tracks = Objects["albums"].get_tracks(object_id)
			union = set(waitlist) & set(tracks)
			if len(union) == len(tracks):
				append = False
				prepend = False
			elif not bool(union):
				delete = False
		if append:
			append_wait_list_action.connect('activate', self._append_to_waitlist, object_id)
			self.append(_("Add to waiting list"), 'app.append_wait_list_action')
		if prepend:
			prepend_wait_list_action.connect('activate', self._prepend_to_waitlist, object_id)
			self.append(_("Play next"), 'app.prepend_wait_list_action')
		if delete:
			del_wait_list_action.connect('activate', self._del_from_waitlist, object_id)
			self.append(_("Remove from waiting list"), 'app.del_wait_list_action')
			
#######################
# PRIVATE             #
#######################		

	"""
		Append track id to waiting list
		@param SimpleAction
		@param GVariant as None
		@param track id as int
	"""
	def _append_to_waitlist(self, action, variant, data):
		if self._is_album:
			for track_id in Objects["albums"].get_tracks(data):
				Objects["player"].append_to_waitlist(track_id)
		else:
			Objects["player"].append_to_waitlist(data)
		
	"""
		Prepend track id to waiting list
		@param SimpleAction
		@param GVariant as None
		@param track id as int
	"""
	def _prepend_to_waitlist(self, action, variant, data):
		if self._is_album:
			for track_id in reversed(Objects["albums"].get_tracks(data)):
				Objects["player"].prepend_to_waitlist(track_id)
		else:
			Objects["player"].prepend_to_waitlist(data)
		
	"""
		Delete track id from waiting list
		@param SimpleAction
		@param GVariant as None
		@param track id as int
	"""
	def _del_from_waitlist(self, action, variant, data):
		if self._is_album:
			for track_id in Objects["albums"].get_tracks(data):
				Objects["player"].del_from_waitlist(track_id)
		else:
			Objects["player"].del_from_waitlist(data)
		
