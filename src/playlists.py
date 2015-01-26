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

from gi.repository import Gtk, Gdk, Gio, GLib, GObject, GdkPixbuf, Pango
from gettext import gettext as _

from _thread import start_new_thread
import os, string
from cgi import escape
from stat import S_ISREG, ST_MTIME, ST_MODE

from lollypop.define import *
from lollypop.albumart import AlbumArt
from lollypop.utils import translate_artist_name

######################################################################
######################################################################


"""
	Playlists manager: add, remove, list, append, ...
"""
class PlaylistsManager(GObject.GObject):

	PLAYLISTS_PATH = os.path.expanduser ("~") +  "/.local/share/lollypop/playlists"
	__gsignals__ = {
		# Add or remove a playlist
		'playlists-changed': (GObject.SIGNAL_RUN_FIRST, None, ()),
		# Objects added/removed to/from playlist
        'playlist-changed': (GObject.SIGNAL_RUN_FIRST, None, (str,)) 
    }

	def __init__(self):
		GObject.GObject.__init__(self)
		self._playlists = []
		self._tracks_cache = {}
		# Create playlists directory if missing
		if not os.path.exists(self.PLAYLISTS_PATH):
			try:
				os.mkdir(self.PLAYLISTS_PATH)
			except Exception as e:
				print("Lollypop::PlaylistsManager::init: %s" % e)

	"""
		Add a playlist
		@param playlist name as str
	"""
	def add(self, playlist_name):
		self._tracks_cache[playlist_name] = []
		try:
			f = open(self.PLAYLISTS_PATH+"/"+playlist_name+".m3u", "w")
			f.write("#EXTM3U\n")
			f.close()
			self.emit('playlists-changed')
		except Exception as e:
			print("PlaylistsManager::add: %s" %e)

	"""
		Rename playlist
		@param new playlist name as str
		@param old playlist name as str
	"""
	def rename(self, new_name, old_name):
		try:
			os.rename(self.PLAYLISTS_PATH+"/"+old_name+".m3u", self.PLAYLISTS_PATH+"/"+new_name+".m3u")
			self.emit('playlists-changed')
		except Exception as e:
			print("PlaylistsManager::rename: %s" %e)

	"""
		delete playlist
		@param playlist name as str
	"""
	def delete(self, playlist_name):
		try:
			os.remove(self.PLAYLISTS_PATH+"/"+playlist_name+".m3u")
			self.emit('playlists-changed')
		except Exception as e:
			print("PlaylistsManager::delete: %s" %e)
			
	"""
		Return availables playlists
		@param max items as int
		@return array of (id, string)
	"""
	def get(self, max_items = None):
		self._playlists = []
		try:
			index = 0
			entries = []
			for filename in os.listdir(self.PLAYLISTS_PATH):
				stat = os.stat(self.PLAYLISTS_PATH+"/"+filename)
				if S_ISREG(stat[ST_MODE]):
					entries.append((stat[ST_MTIME], filename))
			for cdate, filename in sorted(entries):
				if filename.endswith(".m3u"):
					item = (index, filename[:-4])
					self._playlists.append(item)
					index += 1
					# Break if max items is reach
					if max_items and index > max_items:
						break	
		except Exception as e:
			print("Lollypop::PlaylistManager::get: %s" % e)
		return self._playlists

	"""
		Return playlist name for id
		@param playlist id as int
	"""
	def get_name(self, playlist_id):
		for playlist in self._playlists:
			if playlist[0] == playlist_id:
				return playlist[1]
		return ""

	"""
		Return availables tracks for playlist
		@param playlist playlist_name as str
		@return array of track filepath as str
	"""
	def get_tracks(self, playlist_name):
		try:
			tracks = self._tracks_cache[playlist_name]
			return tracks
		except:
			pass
			
		tracks = []
		try:
			f = open(self.PLAYLISTS_PATH+"/"+playlist_name+".m3u", "r")
			for filepath in f:
				if filepath[0] == "/":
					tracks.append(filepath[:-1])
			f.close()
		except Exception as e:
			print("PlaylistsManager::get_tracks: %s" %e)
		self._tracks_cache[playlist_name] = tracks
		return tracks

	"""
		Set playlist tracks
		@param playlist name as str
		@param tracks path as [str]
	"""
	def set_tracks(self, playlist_name, tracks_path):
		self.add(playlist_name)
		for filepath in tracks_path:
			self._add_track(playlist_name, filepath)
		GLib.timeout_add(1000, self.emit, "playlist-changed", playlist_name)

	"""
		Return availables tracks id for playlist
		Thread safe if you pass an sql cursor
		@param playlist name as str
		@return array of track id as int
	"""
	def get_tracks_id(self, playlist_name, sql = None):
		tracks_id = []
		for filepath in self.get_tracks(playlist_name):
			tracks_id.append(Objects.tracks.get_id_by_path(filepath, sql))
		return tracks_id;
		
	"""
		Add track to playlist if not already present
		@param playlist name as str
		@param track filepath as str
	"""
	def add_track(self, playlist_name, filepath):
		self._add_track(playlist_name, filepath)
		GLib.timeout_add(1000, self.emit, "playlist-changed", playlist_name)
		
	"""
		Remove track from playlist
		@param playlist name as str
		@param track filepath as str
	"""
	def remove_track(self, playlist_name, filepath):
		try:
			f = open(self.PLAYLISTS_PATH+"/"+playlist_name+".m3u", "r")
			lines = f.readlines()
			f.close()
			f = open(self.PLAYLISTS_PATH+"/"+playlist_name+".m3u", "w")
			for path in lines:
				if path[:-1] != filepath:
					f.write(path)
			f.close()
			tracks = self.get_tracks(playlist_name)
			tracks.remove(filepath)
			GLib.timeout_add(1000, self.emit, "playlist-changed", playlist_name)
		except Exception as e:
			print("PlaylistsManager::remove_tracks: %s" %e)
			
	"""
		Return True if object_id is already present in playlist
		@param playlist name as str
		@param object id as int
		@param is an album as bool
		@param sql as sqlite cursor
		@return bool
	"""
	def is_present(self, playlist_name, object_id, is_album, sql = None):
		playlist_paths = self.get_tracks(playlist_name)
		if is_album:
			tracks_path = Objects.albums.get_tracks_path(object_id, sql)
		else:
			tracks_path = [ Objects.tracks.get_path(object_id, sql) ]

		found = 0
		len_tracks = len(tracks_path)
		for filepath in tracks_path:
			if filepath in playlist_paths:
				found += 1
				if found >= len_tracks:
					break
		if found == len_tracks:
			return True
		else:
			return False
	
#######################
# PRIVATE             #
#######################
		
	"""
		Add track to playlist if not already present
		@param playlist name as str
		@param track filepath as str
	"""
	def _add_track(self, playlist_name, filepath):
		tracks = self.get_tracks(playlist_name)
		# Do nothing if uri already present in playlist
		if not filepath in tracks:
			try:
				f = open(self.PLAYLISTS_PATH+"/"+playlist_name+".m3u", "a")
				f.write(filepath+'\n')
				f.close()
				tracks.append(filepath)
			except Exception as e:
				print("PlaylistsManager::add_track: %s" %e)
		
"""
	Dialog for manage playlist
"""
class PlaylistsManagePopup:

	"""
		Init Popover ui with a scrolled treeview
		@param object id as int
		@param is album as bool
	"""
	def __init__(self, object_id, is_album):

		self._object_id = object_id		
		self._is_album = is_album
		self._deleted_path = None
		self._del_pixbuf = Gtk.IconTheme.get_default().load_icon("list-remove-symbolic", 22, 0)
		
		self._ui = Gtk.Builder()
		self._ui.add_from_resource('/org/gnome/Lollypop/PlaylistsManagePopup.ui')

		self._model = Gtk.ListStore(bool, str, GdkPixbuf.Pixbuf)

		self._view = self._ui.get_object('view')
		self._view.set_model(self._model)

		self._ui.connect_signals(self)

		self._popup = self._ui.get_object('popup')
		self._infobar = self._ui.get_object('infobar')
		self._infobar_label = self._ui.get_object('infobarlabel')

		if self._object_id != -1:
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
		
		renderer2 = Gtk.CellRendererPixbuf()
		renderer2.set_property('stock-size', 22)
		renderer2.set_fixed_size(22, -1)
		column2 = Gtk.TreeViewColumn("pixbuf2", renderer2, pixbuf=2)
		
		if self._object_id != -1:
			self._view.append_column(column0)
		self._view.append_column(column1)
		self._view.append_column(column2)

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

		start_new_thread(self._append_playlists, ())
		self._popup.show()
		
#######################
# PRIVATE             #
#######################

	"""
		Append playlists, thread safe
	"""
	def _append_playlists(self):
		sql = Objects.db.get_cursor()
		# Search if we need to select item or not
		playlists = Objects.playlists.get()
		for playlist in playlists:
			selected = Objects.playlists.is_present(playlist[1], self._object_id, self._is_album, sql)
			GLib.idle_add(self._append_playlist, playlist[1], selected)

	"""
		Append a playlist
		@param playlist name as str
		@param playlist selected as bool
	"""
	def _append_playlist(self, playlist_name, selected):
		self._model.append([selected, playlist_name, self._del_pixbuf])

	"""
		Show infobar
		@param path as Gtk.TreePath
	"""
	def _show_infobar(self, path):
		iterator = self._model.get_iter(path)
		self._deleted_path = path
		self._infobar_label.set_text(_("Remove \"%s\"?") % self._model.get_value(iterator, 1))
		self._infobar.show()
		
	"""
		Hide infobar
		@param widget as Gtk.Infobar
		@param reponse id as int
	"""
	def _on_response(self, infobar, response_id):
		if response_id == Gtk.ResponseType.CLOSE:
			self._infobar.hide()

	"""
		Delete playlist
		@param TreeView, TreePath, TreeViewColumn
	"""
	def _on_row_activated(self, view, path, column):
		iterator = self._model.get_iter(path)
		if iterator:
			if column.get_title() == "pixbuf2":
				self._show_infobar(path)
			
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
			self._show_infobar(path)
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
		self._model.append([True, name, self._del_pixbuf])
		Objects.playlists.add(name)
		self._set_current_object(name, True)

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
		self._set_current_object(name, toggle)
		
	"""
		Add/Remove current object to playlist
		@param playlist name as str
		@param add as bool
	"""
	def _set_current_object(self, name, add):
		# No current object
		if self._object_id == -1:
			return
		# Add or remove object from playlist
		if self._is_album:
			tracks_path = Objects.albums.get_tracks_path(self._object_id)
		else:
			tracks_path = [ Objects.tracks.get_path(self._object_id) ]

		for track_path in tracks_path:
			if add:
				Objects.playlists.add_track(name, track_path)
			else:
				playlist = Objects.playlists.remove_track(name, track_path)
		
	"""
		When playlist is edited, rename playlist
		@param widget as cell renderer
		@param path as str representation of Gtk.TreePath
		@param name as str
	"""
	def _on_playlist_edited(self, view, path, name):
		if name.find("/") != -1:
			return
		iterator = self._model.get_iter(path)
		old_name = self._model.get_value(iterator, 1)
		self._model.set_value(iterator, 1, name)
		Objects.playlists.rename(name, old_name)
		
		
		
"""
	Dialog for edit a playlist
"""
class PlaylistEditPopup:

	"""
		Init Popover ui with a text entry and a scrolled treeview
		@param playlist name as str
	"""
	def __init__(self, playlist_name):

		self._playlist_name = playlist_name
		self._deleted_path = None
		self._del_pixbuf = Gtk.IconTheme.get_default().load_icon("list-remove-symbolic", 22, 0)
		
		self._ui = Gtk.Builder()
		self._ui.add_from_resource('/org/gnome/Lollypop/PlaylistEditPopup.ui')

		self._model = Gtk.ListStore(GdkPixbuf.Pixbuf, str, GdkPixbuf.Pixbuf, str)

		self._view = self._ui.get_object('view')
		self._view.set_model(self._model)

		self._ui.connect_signals(self)

		self._entry = self._ui.get_object('entry')
		self._popup = self._ui.get_object('popup')
		self._infobar = self._ui.get_object('infobar')
		self._infobar_label = self._ui.get_object('infobarlabel')

		renderer0 = Gtk.CellRendererPixbuf()
		renderer0.set_property('stock-size', ART_SIZE_MEDIUM)
		column0 = Gtk.TreeViewColumn("pixbuf1", renderer0, pixbuf=0)
		
		renderer1 = Gtk.CellRendererText()
		renderer1.set_property('ellipsize-set',True)
		renderer1.set_property('ellipsize', Pango.EllipsizeMode.END)
		column1 = Gtk.TreeViewColumn("text1", renderer1, markup=1)
		column1.set_expand(True)
		
		renderer2 = Gtk.CellRendererPixbuf()
		renderer2.set_property('stock-size', 22)
		renderer2.set_fixed_size(22, -1)
		column2 = Gtk.TreeViewColumn("pixbuf2", renderer2, pixbuf=2)
		
		self._view.append_column(column0)
		self._view.append_column(column1)
		self._view.append_column(column2)

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

		start_new_thread(self._append_tracks, ())
		self._popup.show()
		
#######################
# PRIVATE             #
#######################

	"""
		Append tracks, thread safe
	"""
	def _append_tracks(self):
		sql = Objects.db.get_cursor()
		tracks = Objects.playlists.get_tracks_id(self._playlist_name, sql)
		GLib.idle_add(self._append_track, tracks)

	"""
		Append track while tracks not empty
		@param tracks as [track_id as int]
	"""
	def _append_track(self, tracks):
		if len(tracks) > 0:
			track_id = tracks.pop(0)
			filepath = Objects.tracks.get_path(track_id)
			album_id = Objects.tracks.get_album_id(track_id)
			artist_id = Objects.tracks.get_performer_id(track_id)
			if artist_id == COMPILATIONS:
				artist_id = Objects.tracks.get_artist_id(track_id)
			artist_name = Objects.artists.get_name(artist_id)
			track_name = Objects.tracks.get_name(track_id)
			art = Objects.art.get(album_id, ART_SIZE_SMALL)
			self._model.append([art, "<b>"+escape(translate_artist_name(artist_name)) + "</b>\n" + 
								escape(track_name), self._del_pixbuf, filepath])
			GLib.idle_add(self._append_track, tracks)

	"""
		Delete item if Delete was pressed
		@param widget unused, Gtk.Event
	"""
	def _on_keyboard_event(self, widget, event):
		if event.keyval == 65535:
			path, column = self._view.get_cursor()
			self._show_infobar(path)
			
	"""
		Show infobar
		@param path as Gtk.TreePath
	"""
	def _show_infobar(self, path):
		iterator = self._model.get_iter(path)
		self._deleted_path = path
		self._infobar_label.set_markup(_("Remove \"%s\"?") % self._model.get_value(iterator, 1).replace('\n',' - '))
		self._infobar.show()
		
	"""
		Hide infobar
		@param widget as Gtk.Infobar
		@param reponse id as int
	"""
	def _on_response(self, infobar, response_id):
		if response_id == Gtk.ResponseType.CLOSE:
			self._infobar.hide()

	"""
		Delete playlist
		@param TreeView, TreePath, TreeViewColumn
	"""
	def _on_row_activated(self, view, path, column):
		iterator = self._model.get_iter(path)
		if iterator:
			if column.get_title() == "pixbuf2":
				self._show_infobar(path)
			
	"""
		Delete playlist after confirmation
		@param button as Gtk.Button
	"""
	def _on_delete_confirm(self, button):
		if self._deleted_path:
			iterator = self._model.get_iter(self._deleted_path)
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
			self._show_infobar(path)
	"""
		Hide window
		@param widget as Gtk.Button
	"""
	def _on_close_clicked(self, widget):
		self._popup.hide()
		tracks_path = []
		for item in self._model:
			tracks_path.append(item[3])
		Objects.playlists.set_tracks(self._playlist_name, tracks_path)
		self._model.clear()
