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

from gi.repository import Gtk, Gdk, GLib, GObject, GdkPixbuf, Pango
from gettext import gettext as _, ngettext 

import os

from lollypop.define import *
from lollypop.albumart import AlbumArt
from lollypop.utils import translate_artist_name

######################################################################
######################################################################


"""
	Playlists manager: add, remove, list, append, ...
"""
class PlaylistsManager:

	PLAYLISTS_PATH = os.path.expanduser ("~") +  "/.local/share/lollypop/playlists"

	def __init__(self):
		self._playlists = [] #Cache
		# Create playlists directory if missing
		if not os.path.exists(self.PLAYLISTS_PATH):
			try:
				os.mkdir(self.PLAYLISTS_PATH)
			except Exception as e:
				print("Lollypop::PlaylistsManager::init: %s" % e)

	"""
		Return availables playlists
		@return array of (id, string)
	"""
	def get(self):
		self._playlists = []
		try:
			index = 0
			for filename in os.listdir(self.PLAYLISTS_PATH):
				item = (index, filename)
				self._playlists.append(item)
				index += 1		
		except Exception as e:
			print("Lollypop::PlaylistManager::get: %s" % e)
		return self._playlists

	"""
		Return availables tracks for playlist
		@param playlist name as str
		@return array of track id as int
	"""
	def get_tracks(self, playlist):
		return []

	"""
		Add track to playlist
		@param track id as int
		@param playlist name as str
	"""
	def add_track(self, track_id, playlist):
		pass

	"""
		Remove track from playlist
		@param track id as int
		@param playlist name as str
	"""
	def remove_track(self, track_id, playlist):
		pass

"""
	Dialog for adding/removing a song to/from a playlist
"""
class PlaylistPopup:

	"""
		Init Popover ui with a text entry and a scrolled treeview
		@param object id as int
		@param is album as bool
	"""
	def __init__(self, object_id, is_album):

		self._object_id = object_id		
		self._is_album = is_album
		self._deleted_path = None

		self._ui = Gtk.Builder()
		self._ui.add_from_resource('/org/gnome/Lollypop/PlaylistPopup.ui')

		self._model = Gtk.ListStore(bool, str)

		self._view = self._ui.get_object('view')
		self._view.set_model(self._model)

		self._ui.connect_signals(self)

		self._popup = self._ui.get_object('popup')
		self._infobar = self._ui.get_object('infobar')
		self._infobar_label = self._ui.get_object('infobarlabel')

		renderer0 = Gtk.CellRendererToggle()
		renderer0.set_property('activatable', True)
		renderer0.connect('toggled', self._on_playlist_toggled)
		column0 = Gtk.TreeViewColumn("toggle", renderer0, active=0)
		
		renderer1 = Gtk.CellRendererText()
		renderer1.set_property('ellipsize-set',True)
		renderer1.set_property('ellipsize', Pango.EllipsizeMode.END)
		renderer1.set_property('editable', True)
		renderer1.connect('edited', self._on_playlist_edited)
		column1 = Gtk.TreeViewColumn('text', renderer1, text=1)
		column1.set_expand(True)
		
		
		self._view.append_column(column0)
		self._view.append_column(column1)

	"""
		Show playlist popup
	"""
	def show(self):
		self._popup.set_property('width-request', 600)
		size_setting = Objects.settings.get_value('window-size')
		if isinstance(size_setting[1], int):
			self._popup.set_property('height-request', size_setting[1]*0.5)
		else:
			self._popup.set_property('height-request', 600)

		# Select playlist if one song at least is present in album
		selected = False
		if self._is_album:
			tracks = Objects.albums.get_tracks(self._object_id)
		else:
			tracks = [ self._object_id ]

		playlists = Objects.playlists.get()
		for playlist in playlists:
			for track in Objects.playlists.get_tracks(playlist[1]):
				if track in tracks:
					selected = True
			self._model.append([selected, playlist[1]])
		self._popup.show()
		
#######################
# PRIVATE             #
#######################

	"""
		Hide infobar
		@param widget as Gtk.Infobar
		@param reponse id as int
	"""
	def _on_response(self, infobar, response_id):
		if response_id == Gtk.ResponseType.CLOSE:
			self._infobar.hide()

	"""
		Delete playlist after confirmation
		@param button as Gtk.Button
	"""
	def _on_delete_confirm(self, button):
		if self._deleted_path:
			iterator = self._model.get_iter(self._deleted_path)
			Objects.playlists.delete(self._model.get_value(iterator, 1))
			self._model.remove(iterator)
			self._deleted_path = None
			self._infobar.hide()

	"""
		Delete item if Delete was pressed
		@param widget unused, Gtk.Event
	"""
	def _on_keyboard_event(self, widget, event):
		if event.keyval == 65535:
			path, column = self._view.get_cursor()
			iterator = self._model.get_iter(path)
			self._deleted_path = path
			self._infobar_label.set_text(_("Remove %s playlist?") % self._model.get_value(iterator, 1))
			self._infobar.show()

	"""
		Hide window
		@param widget as Gtk.Button
	"""
	def _on_close_clicked(self, widget):
		self._popup.hide()
		self._model.clear()

	"""
		Add new playlist
		@param widget as Gtk.Button
	"""
	def _on_new_clicked(self, widget):
		existing_playlists = []
		for item in self._model:
			existing_playlists.append(item[1])

		# Search for an available name
		count = len(self._model) + 1
		name = _("New playlist ")+str(count)
		while name in existing_playlists:
			count += 1
			name = _("New playlist ")+str(count)
		self._model.append([True, name])
		Objects.playlists.add(name)

	"""
		When playlist is activated, add object to playlist
		@param widget as cell renderer
		@param path as str representation of Gtk.TreePath
	"""
	def _on_playlist_toggled(self, view, path):
		iterator = self._model.get_iter(path)
		toggle = not self._model.get_value(iterator, 0)
		name = self._model.get_value(iterator, 1)
		self._model.set_value(iterator, 0, toggle)

		# Add or remove object from playlist
		if self._is_album:
			tracks = Objects.albums.get_tracks(self._object_id)
		else:
			tracks = [ self._object_id ]

		for track_id in tracks:
			if toggle:
				Objects.playlists.add_track(track_id, name)
			else:
				Objects.playlists.remove_track(track_id, name)
			
		
	"""
		When playlist is edited, rename playlist
		@param widget as cell renderer
		@param path as str representation of Gtk.TreePath
		@param text as str
	"""
	def _on_playlist_edited(self, view, path, text):
		iterator = self._model.get_iter(path)
		name = self._model.get_value(iterator, 1)
		self._model.set_value(iterator, 1, text)
		Objects.playlists.rename(text, name)
