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

from gettext import gettext as _
from gi.repository import Gtk, GObject, GLib, Gio
from _thread import start_new_thread

from lollypop.define import *
from lollypop.playlists import PlaylistEditPopup

class PopPlaylistMenu(Gio.Menu):
	"""
		Init menu model
		@param: playlist name as str
	"""
	def __init__(self, playlist_name):
		Gio.Menu.__init__(self)
		app = Gio.Application.get_default()
		#FIXME How signal connect works when called many times

		edit_playlist_action = Gio.SimpleAction(name="edit_playlist_action")
		app.add_action(edit_playlist_action)
		edit_playlist_action.connect('activate', self._edit, playlist_name)
		self.append(_("Edit playlist"), 'app.edit_playlist_action')
			
#######################
# PRIVATE             #
#######################		

	"""
		Edit playlist
		@param SimpleAction
		@param GVariant
		@param playlist name as str
	"""
	def _edit(self, action, variant, playlist_name):
		popup = PlaylistEditPopup(playlist_name)
		popup.show()
