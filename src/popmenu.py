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
import urllib.request
import urllib.parse
from _thread import start_new_thread

from lollypop.define import *

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
		#FIXME How signal connect works when called many times
		play_album_action = Gio.SimpleAction(name="play_album_action")
		app.add_action(play_album_action)
		append_queue_action = Gio.SimpleAction(name="append_queue_action")
		app.add_action(append_queue_action)
		prepend_queue_action = Gio.SimpleAction(name="prepend_queue_action")
		app.add_action(prepend_queue_action)
		del_queue_action = Gio.SimpleAction(name="del_queue_action")
		app.add_action(del_queue_action)
		queue = Objects.player.get_queue()
		append = True
		prepend = True
		delete = True
		if len(queue) == 0:
			append = False
		if not is_album:
			if object_id in queue:
				if len(queue) > 0 and queue[0] == object_id:
					prepend = False
				append = False
			else:
				delete = False
		else:
			play_album_action.connect('activate', self._play_album, object_id)
			self.append(_("Only play this album"), 'app.play_album_action')
			tracks = Objects.albums.get_tracks(object_id)
			union = set(queue) & set(tracks)
			if len(union) == len(tracks):
				append = False
				prepend = False
			elif not bool(union):
				delete = False
		if append:
			append_queue_action.connect('activate', self._append_to_queue, object_id)
			self.append(_("Add to queue"), 'app.append_queue_action')
		if prepend:
			prepend_queue_action.connect('activate', self._prepend_to_queue, object_id)
			if is_album:
				self.append(_("Next tracks"), 'app.prepend_queue_action')
			else:
				self.append(_("Next track"), 'app.prepend_queue_action')
		if delete:
			del_queue_action.connect('activate', self._del_from_queue, object_id)
			self.append(_("Remove from queue"), 'app.del_queue_action')
			
#######################
# PRIVATE             #
#######################		

	"""
		Play album
		@param SimpleAction
		@param GVariant as None
		@param album id as int
	"""
	def _play_album(self, action, variant, album_id):
		Objects.player.play_album(album_id)

	"""
		Append track to queue
		@param SimpleAction
		@param GVariant as None
		@param album id as int
	"""
	def _append_to_queue(self, action, variant, album_id):
		if self._is_album:
			for track_id in Objects.albums.get_tracks(album_id):
				Objects.player.append_to_queue(track_id)
		else:
			Objects.player.append_to_queue(album_id)
		
	"""
		Prepend track id to queue
		@param SimpleAction
		@param GVariant as None
		@param album id as int
	"""
	def _prepend_to_queue(self, action, variant, album_id):
		if self._is_album:
			for track_id in reversed(Objects.albums.get_tracks(album_id)):
				Objects.player.prepend_to_queue(track_id)
		else:
			Objects.player.prepend_to_queue(album_id)
		
	"""
		Delete track id from queue
		@param SimpleAction
		@param GVariant as None
		@param album id as int
	"""
	def _del_from_queue(self, action, variant, album_id):
		if self._is_album:
			for track_id in Objects.albums.get_tracks(album_id):
				Objects.player.del_from_queue(track_id)
		else:
			Objects.player.del_from_queue(album_id)
		
