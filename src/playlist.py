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

from gi.repository import Gtk, Gdk, GLib, GObject, GdkPixbuf, Pango
from gettext import gettext as _, ngettext 

from lollypop.config import *
from lollypop.albumart import AlbumArt
from lollypop.utils import translate_artist_name

class CellRendererButton(Gtk.CellRenderer):
	def __init__(self):
		Gtk.CellRenderer.__init__(self)

	def do_get_size(self, widget, cell_area):
		btn_height = 0
		btn_width = 0
		if cell_area:
			btn_height = cell_area.height
			btn_width = btn_height
		return (0, 0, btn_width, btn_height)

	def do_render(self, cr, widget, background_area, cell_area, flags):
		x, y, btn_width, btn_height = self.get_size(widget, cell_area)
		Gtk.paint_box(widget.get_style(), cr, widget.get_state(), Gtk.ShadowType.ETCHED_OUT,
		              widget, None, 0, 0, btn_width, btn_height)

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

		self._model = Gtk.ListStore(GdkPixbuf.Pixbuf, str, int)
		self._view = Gtk.TreeView(self._model)
		self._view.set_property("activate-on-single-click", True)
		self._view.set_property("reorderable", True)
		renderer0 = Gtk.CellRendererPixbuf()
		renderer0.set_property('stock-size', 16)
		renderer1 = Gtk.CellRendererText()
		renderer1.set_property('ellipsize-set',True)
		renderer1.set_property('ellipsize', Pango.EllipsizeMode.END)
		renderer2 = CellRendererButton()

		self._view.append_column(Gtk.TreeViewColumn(None, renderer0, pixbuf=0))
		self._view.append_column(Gtk.TreeViewColumn(None, renderer1, markup=1))
		#self._view.append_column(Gtk.TreeViewColumn(None, renderer2, label=2))
		self._view.set_headers_visible(False)
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
		self._model.clear()
		tracks = Objects["player"].get_playlist()
		if len(tracks) > 0:
			for track_id in tracks:
				album_id = Objects["tracks"].get_album_id(track_id)
				artist_id = Objects["albums"].get_artist_id(album_id)
				artist_name = Objects["artists"].get_name(artist_id)
				track_name = Objects["tracks"].get_name(track_id)
				art = Objects["art"].get(album_id, ART_SIZE_MEDIUM)
				self._model.append([art, "<b>"+translate_artist_name(artist_name) + "</b>\n" + track_name, track_id])
				
		else:
			self._model.append([None, _("Right click on a song to add it to playlist"), None])
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
	def _reordered_playlist(self, view, path):
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
		if value_id != -1:
			Objects["player"].del_from_playlist(value_id)
			Objects["player"].load(value_id)
			view.remove(row)
			row.destroy()
