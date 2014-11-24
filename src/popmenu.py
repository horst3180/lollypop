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
	"""
	def __init__(self, track_id):
		Gio.Menu.__init__(self)
		app = Gio.Application.get_default()
		wait_list_action = Gio.SimpleAction(name="wait_list_action")
		app.add_action(wait_list_action)
		waitlist = Objects["player"].get_waitlist()
		if track_id in waitlist:
			wait_list_action.connect('activate', self._del_from_waitlist, track_id)
			self.append(_("Remove from waiting list"), 'app.wait_list_action')
		else:
			wait_list_action.connect('activate', self._add_to_waitlist, track_id)
			self.append(_("Add to waiting list"), 'app.wait_list_action')
		
#######################
# PRIVATE             #
#######################		

	"""
		Add track id to waiting list
		@param SimpleAction
		@param GVariant as None
		@param track id as int
	"""
	def _add_to_waitlist(self, action, variant, data):
		Objects["player"].add_to_waitlist(data)
		
	"""
		Delete track id from waiting list
		@param SimpleAction
		@param GVariant as None
		@param track id as int
	"""
	def _del_from_waitlist(self, action, variant, data):
		Objects["player"].del_from_waitlist(data)
		
