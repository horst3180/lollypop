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
# Many code inspiration from gnome-music at the GNOME project

from gi.repository import Gtk, Gdk, GLib, GdkPixbuf, Pango
from gettext import gettext as _, ngettext 

from lollypop.config import *
from lollypop.albumart import AlbumArt
from lollypop.utils import translate_artist_name


class PlayListRow(Gtk.ListBoxRow):
	"""
		Init row widgets
	"""
	def __init__(self):
		Gtk.ListBoxRow.__init__(self)
		self._object_id = None
		self._is_track = False
		self._ui = Gtk.Builder()
		self._ui.add_from_resource('/org/gnome/Lollypop/PlayListRow.ui')
		self._row_widget = self._ui.get_object('row')
		self._artist = self._ui.get_object('artist')
		self._title = self._ui.get_object('title')
		self._cover = self._ui.get_object('cover')
		self._button = self._ui.get_object('delete')
		self._button.connect("clicked", self.destroy_callback)
		self.add(self._row_widget)
		self.show()

	
	"""
		Destroy all widgets
	"""
	def destroy(self):
		self.remove(self._row_widget)
		for widget in self._ui.get_objects():
			widget.destroy()
		Gtk.ListBoxRow.destroy(self)

	"""
		Destroy widget
	"""
	def destroy_callback(self, event):
		self.destroy()

	"""
		Set artist label
		arg: untranslated artist name as string
	"""
	def set_artist(self, name):
		self._artist.set_text(translate_artist_name(name))

	"""
		Set title label
		arg: title as string
	"""
	def set_title(self, name):
		self._title.set_text(name)

	"""
		Show message about how to use playlist
	"""
	def show_help(self):
		self._button.hide()
		self._title.hide()
		self._cover.hide()
		self._artist.set_text(_("Right click on a song to add it to playlist"))
	
	"""
		Set cover pixbuf
		arg: pixbuf
	"""
	def set_cover(self, pixbuf):
		self._cover.set_from_pixbuf(pixbuf)

	"""
		Store current object id
		arg: object id as int
	"""
	def set_object_id(self, object_id):
		self._object_id = object_id

	"""
		Current object id
		ret: object id as int
	"""
	def get_object_id(self):
		return self._object_id

	"""
		True if button is active
		ret: bool
	"""
	def is_button_active(self):
		return self._button.get_active()


######################################################################
######################################################################

class PlayListWidget(Gtk.Popover):

	"""
		Init Popover ui with a text entry and a scrolled treeview
	"""
	def __init__(self):
		Gtk.Popover.__init__(self)
		
		self._timeout = None
		self._row_signal = None

		self._view = Gtk.ListBox()
		self._view.connect("row-activated", self._on_activate)	
		self._view.connect("remove", self._on_remove)

		self._view.show()

		self.set_property('width-request', 500)
		self.set_property('height-request', 700)
		self._scroll = Gtk.ScrolledWindow()
		self._scroll.set_hexpand(True)
		self._scroll.set_vexpand(True)
		self._scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
		self._scroll.add(self._view)
		self._scroll.show_all()

		self.add(self._scroll)

	"""
		Show playlist popover		
		Populate treeview with current playlist
	"""
	def show(self):
		self._clear()
		tracks = Objects["player"].get_playlist()
		if len(tracks) > 0:
			for track_id in tracks:
				album_id = Objects["tracks"].get_album_id(track_id)
				artist_id = Objects["artists"].get_id(album_id)
				art = Objects["art"].get(album_id, ART_SIZE_MEDIUM)
				playlist_row = PlayListRow()
				playlist_row.set_artist(Objects["artists"].get_name(artist_id))
				playlist_row.set_title(Objects["tracks"].get_name(track_id))
				playlist_row.set_cover(art)
				playlist_row.set_object_id(track_id)
				self._view.add(playlist_row)
		else:
			playlist_row = PlayListRow()
			playlist_row.show_help()
			self._view.add(playlist_row)
		Gtk.Popover.show(self)

#######################
# PRIVATE             #
#######################

	"""
		Clear widget removing every row, use it when widget isn't visible
	"""
	def _clear(self):
		for child in self._view.get_children():
			child.destroy()

	"""
		Delete item when item have been destroyed
	"""
	def _on_remove(self, container, widget):
		# Do not remove items if we are just calling _clear()
		if self.is_visible():
			new_playlist = []
			for child in self._view.get_children():
				new_playlist.append(child.get_object_id())
			Objects["player"].set_playlist(new_playlist)

	"""
		Update playlist order after user drag&drop reorder
		arg: row, row
	"""
	def _reordered_playlist(self, row1 ,row2):
		return
		new_playlist = []
		for row in self._model:
			if row[2]:
				new_playlist.append(row[2])
		Objects["player"].set_playlist(new_playlist)

	"""
		Play clicked item
		arg: view, row
	"""
	def _on_activate(self, view, row):
		
		value_id = row.get_object_id()
		Objects["player"].del_from_playlist(value_id)
		Objects["player"].load(value_id)
		view.remove(row)
		row.destroy()
