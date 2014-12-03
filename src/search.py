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

from gi.repository import Gtk, GLib, GdkPixbuf, Pango
from gettext import gettext as _

from lollypop.config import *
from lollypop.albumart import AlbumArt
from lollypop.utils import translate_artist_name

class SearchRow(Gtk.ListBoxRow):
	"""
		Init row widgets
	"""
	def __init__(self):
		Gtk.ListBoxRow.__init__(self)
		self._object_id = None
		self._is_track = False
		self._ui = Gtk.Builder()
		self._ui.add_from_resource('/org/gnome/Lollypop/SearchRow.ui')
		self._row_widget = self._ui.get_object('row')
		self._artist = self._ui.get_object('artist')
		self._item = self._ui.get_object('item')
		self._cover = self._ui.get_object('cover')
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
		Set artist label
		@param untranslated artist name as string
	"""
	def set_artist(self, name):
		self._artist.set_text(translate_artist_name(name))

	"""
		Set item label
		@param item name as string
	"""
	def set_item(self, name):
		self._item.set_text(name)

	"""
		Set cover pixbuf
		@param pixbuf
	"""
	def set_cover(self, pixbuf):
		self._cover.set_from_pixbuf(pixbuf)

	"""
		Store current object id
		@param object id as int
	"""
	def set_object_id(self, object_id):
		self._object_id = object_id

	"""
		Get object id
		@return Current object id as int
	"""
	def get_object_id(self):
		return self._object_id

	"""
		Mark object as a track
	"""
	def track(self):
		self._is_track = True

	"""
		True if it's a track
		@return bool
	"""
	def is_track(self):
		return self._is_track

######################################################################
######################################################################

class SearchWidget(Gtk.Popover):

	"""
		Init Popover ui with a text entry and a scrolled treeview
	"""
	def __init__(self):
		Gtk.Popover.__init__(self)
		
		self._timeout = None

		self.set_property('width-request', 400)

		grid = Gtk.Grid()
		grid.set_property("orientation", Gtk.Orientation.VERTICAL)

		label = Gtk.Label(_("Search:"))
		label.set_property("margin_start", 5)
		label.set_property("margin_end", 5)
		label.show()
		
		self._text_entry = Gtk.Entry()
		self._text_entry.connect("changed", self._do_filtering)
		self._text_entry.set_hexpand(True)
		self._text_entry.set_property("margin", 5)
		self._text_entry.show()
		
		entry_line = Gtk.Grid()
		entry_line.add(label)
		entry_line.add(self._text_entry)
		entry_line.show()
		
		self._view = Gtk.ListBox()
		self._view.connect("row-activated", self._on_activate)	
		self._view.show()		
		
		self._scroll = Gtk.ScrolledWindow()
		self._scroll.set_vexpand(True)
		self._scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
		self._scroll.add(self._view)
		self._scroll.show()

		grid.add(entry_line)
		grid.add(self._scroll)
		grid.show()
		self.add(grid)

#######################
# PRIVATE             #
#######################
	
	"""
		Give focus to text entry on show
	"""
	def do_show(self):
		size_setting = Objects["settings"].get_value('window-size')
		if isinstance(size_setting[1], int):
			self.set_property('height-request', size_setting[1]*0.7)
		else:
			self.set_property('height-request', 600)
		self._text_entry.grab_focus()
		Gtk.Popover.do_show(self)

	"""
		Clear widget removing every row
	"""
	def _clear(self):
		for child in self._view.get_children():
			child.destroy()

	"""
		Timeout filtering, call _really_do_filterting() after a small timeout
	"""	
	def _do_filtering(self, data):
		if self._timeout:
			GLib.source_remove(self._timeout)
		if self._text_entry.get_text() != "":
			self._timeout = GLib.timeout_add(500, self._really_do_filtering)
		else:
			self._clear()

	"""
		Populate treeview searching items in db based on text entry current text
	"""
	def _really_do_filtering(self):
		self._timeout = None
		self._clear()
		searched = self._text_entry.get_text()

		albums = Objects["albums"].search(searched)
		tracks_non_performer = []
		
		for artist_id in Objects["artists"].search(searched):
			for album_id in Objects["albums"].get_ids(artist_id, None):
				if (album_id, artist_id) not in albums:
					albums.append((album_id, artist_id))
			for track_id, track_name in Objects["tracks"].get_as_non_performer(artist_id):
				tracks_non_performer.append((track_id, track_name))

		for album_id, artist_id in albums:
			artist_name = Objects["artists"].get_name(artist_id)
			album_name = Objects["albums"].get_name(album_id)
			search_row = SearchRow()
			search_row.set_artist(artist_name)
			search_row.set_item(album_name)
			search_row.set_cover(Objects["art"].get(album_id,  ART_SIZE_MEDIUM))
			search_row.set_object_id(album_id)			
			self._view.add(search_row)

		for track_id, track_name in Objects["tracks"].search(searched)+tracks_non_performer:
			album_id = Objects["tracks"].get_album_id(track_id)
			artist_id = Objects["tracks"].get_artist_id(track_id)
			artist_name = Objects["artists"].get_name(artist_id)
			search_row = SearchRow()
			search_row.set_artist(artist_name)
			search_row.set_item(track_name)
			search_row.set_cover(Objects["art"].get(album_id, ART_SIZE_MEDIUM))
			search_row.set_object_id(track_id)
			search_row.track()
			self._view.add(search_row)

		
	"""
		Play searched item when selected
		If item is an album, play first track
	"""
	def _on_activate(self, widget, row):
		value_id = row.get_object_id()
		if row.is_track():
			Objects["player"].load(value_id)
		else:
			genre_id = Objects["albums"].get_genre(value_id)
			# Get first track from album
			track_id = Objects["albums"].get_tracks(value_id)[0]
			Objects["player"].load(track_id)
			if not Objects["player"].is_party():
				album_id = Objects["tracks"].get_album_id(track_id)
				Objects["player"].set_album(album_id, track_id)


