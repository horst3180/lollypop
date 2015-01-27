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
from lollypop.playlists import *

class PopMainMenu(Gio.Menu):
	"""
		Init menu model
		@param: object id as int
		@param: is album as bool
		@param: toolbar context as bool => only show playlists
	"""
	def __init__(self, object_id, is_album, toolbar_context = False):
		Gio.Menu.__init__(self)
		self._is_album = is_album
		app = Gio.Application.get_default()
		#FIXME How signal connect works when called many times
		
		if not toolbar_context:
			playback_menu = Gio.Menu()
			if is_album:
				self._set_album_actions(app, playback_menu, object_id)
			self._set_queue_actions(app, playback_menu, object_id, is_album)
			self.insert_section(0, _("Playback"), playback_menu)

		playlist_menu = Gio.Menu()
		self._set_playlist_actions(app, playlist_menu, object_id, is_album)

		self.insert_section(1, _("Playlists"), playlist_menu)
			
#######################
# PRIVATE             #
#######################		

	"""
		Set album actions
		@param app as Gio.Application
		@param menu as Gio.Menu
		@param object_id as int
	"""
	def _set_album_actions(self, app, menu, object_id):
		play_album_action = Gio.SimpleAction(name="play_album_action")
		app.add_action(play_album_action)
		play_album_action.connect('activate', self._play_album, object_id)
		menu.append(_("Only play this album"), 'app.play_album_action')
		
	"""
		Set playlist actions
		@param app as Gio.Application
		@param menu as Gio.Menu
		@param object_id as int
		@param is album as bool
	"""
	def _set_playlist_actions(self, app, menu, object_id, is_album):
		playlist_action = Gio.SimpleAction(name="playlist_action")
		app.add_action(playlist_action)
		playlist_action.connect('activate', self._add_to_playlists, object_id, is_album)
		menu.append(_("Add to others"), 'app.playlist_action')
	
		i = 0
		for playlist in Objects.playlists.get_last():
			action = Gio.SimpleAction(name="playlist%s" % i)
			app.add_action(action)
			if Objects.playlists.is_present(playlist, object_id, is_album):
				action.connect('activate', self._del_from_playlist, object_id, is_album, playlist)
				menu.append(_("Remove from \"%s\"") % playlist, "app.playlist%s" % i)
			else:
				action.connect('activate', self._add_to_playlist, object_id, is_album, playlist)
				menu.append(_("Add to \"%s\"") % playlist, "app.playlist%s" % i)
			i+=1
	
	"""
		Set queue actions
		@param app as Gio.Application
		@param menu as Gio.Menu
		@param object_id as int
		@param is album as bool
	"""	
	def _set_queue_actions(self, app, menu, object_id, is_album):
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
		
			tracks = Objects.albums.get_tracks(object_id)
			union = set(queue) & set(tracks)
			if len(union) == len(tracks):
				append = False
				prepend = False
			elif not bool(union):
				delete = False
				
		append_queue_action = Gio.SimpleAction(name="append_queue_action")
		app.add_action(append_queue_action)
		prepend_queue_action = Gio.SimpleAction(name="prepend_queue_action")
		app.add_action(prepend_queue_action)
		del_queue_action = Gio.SimpleAction(name="del_queue_action")
		app.add_action(del_queue_action)
		if append:
			append_queue_action.connect('activate', self._append_to_queue, object_id)
			menu.append(_("Add to queue"), 'app.append_queue_action')
		if prepend:
			prepend_queue_action.connect('activate', self._prepend_to_queue, object_id)
			if is_album:
				menu.append(_("Next tracks"), 'app.prepend_queue_action')
			else:
				menu.append(_("Next track"), 'app.prepend_queue_action')
		if delete:
			del_queue_action.connect('activate', self._del_from_queue, object_id)
			menu.append(_("Remove from queue"), 'app.del_queue_action')
			
	"""
		Play album
		@param SimpleAction
		@param GVariant
		@param album id as int
	"""
	def _play_album(self, action, variant, album_id):
		Objects.player.play_album(album_id)

	"""
		Add to playlists
		@param SimpleAction
		@param GVariant
		@param object id as int
		@param is album as bool
	"""
	def _add_to_playlists(self, action, variant, object_id, is_album):
		popup = PlaylistsManagePopup(object_id, is_album)
		popup.show()

	"""
		Add to playlist
		@param SimpleAction
		@param GVariant
		@param object id as int
		@param is album as bool
		@param playlist name as str
	"""
	def _add_to_playlist(self, action, variant, object_id, is_album, playlist_name):
		if is_album:
			tracks_path = Objects.albums.get_tracks_path(object_id)
		else:
			tracks_path = [ Objects.tracks.get_path(object_id) ]

		start_new_thread(Objects.playlists.add_tracks, (playlist_name, tracks_path))
		
	"""
		Del from playlist
		@param SimpleAction
		@param GVariant
		@param object id as int
		@param is album as bool
		@param playlist name as str
	"""
	def _del_from_playlist(self, action, variant, object_id, is_album, playlist_name):
		if is_album:
			tracks_path = Objects.albums.get_tracks_path(object_id)
		else:
			tracks_path = [ Objects.tracks.get_path(object_id) ]

		start_new_thread(Objects.playlists.remove_tracks, (playlist_name, tracks_path))
			
	"""
		Append track to queue
		@param SimpleAction
		@param GVariant
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
		@param GVariant
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
		@param GVariant
		@param album id as int
	"""
	def _del_from_queue(self, action, variant, album_id):
		if self._is_album:
			for track_id in Objects.albums.get_tracks(album_id):
				Objects.player.del_from_queue(track_id)
		else:
			Objects.player.del_from_queue(album_id)
		
