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
from _thread import start_new_thread

from lollypop.define import *
from lollypop.albumart import AlbumArt
from lollypop.utils import translate_artist_name

class SearchRow(Gtk.ListBoxRow):
	"""
		Init row widgets
	"""
	def __init__(self):
		Gtk.ListBoxRow.__init__(self)
		self.id = None
		self.is_track = False
		self._ui = Gtk.Builder()
		self._ui.add_from_resource('/org/gnome/Lollypop/SearchRow.ui')
		self._row_widget = self._ui.get_object('row')
		self._artist = self._ui.get_object('artist')
		self._item = self._ui.get_object('item')
		self._cover = self._ui.get_object('cover')
		self._ui.get_object('add').connect('clicked', self._on_add_clicked)
		self._ui.get_object('next').connect('clicked', self._on_next_clicked)
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
	def set_title(self, name):
		self._item.set_text(name)

	"""
		Set cover pixbuf
		@param pixbuf
	"""
	def set_cover(self, pixbuf):
		self._cover.set_from_pixbuf(pixbuf)

#######################
# PRIVATE             #
#######################
	"""
		Return True if item exist results
		@param: items as array of searchObject
	"""
	def _exists(self, items):
		found = False
		for item in items:
			if item.is_track and self.is_track:
				if item.id == self.id:
					found = True
					break
			elif not item.is_track and not self.is_track:
				if item.id == self.id:
					found = True
					break
		return found

	"""
		Add track to queue
		@param button as Gtk.Button
	"""
	def _on_add_clicked(self, button):
		if self.is_track:
			Objects.player.append_to_queue(self.id)
		else:
			for track in Objects.albums.get_tracks(self.id):
				Objects.player.append_to_queue(track)
		button.hide()

	"""
		Prepend track to queue
		@param button as Gtk.Button
	"""
	def _on_next_clicked(self, button):
		if self.is_track:
			Objects.player.prepend_to_queue(self.id)
		else:
			for track in reversed(Objects.albums.get_tracks(self.id)):
				Objects.player.prepend_to_queue(track)
		button.hide()

######################################################################
######################################################################

class SearchObject:
	def __init__(self):
		self.artist = None
		self.title = None
		self.count = -1
		self.id = None
		self.album_id = None
		self.is_track = False

######################################################################
######################################################################

class SearchWidget(Gtk.Popover):

	"""
		Init Popover ui with a text entry and a scrolled treeview
	"""
	def __init__(self):
		Gtk.Popover.__init__(self)
		
		self._in_thread = False
		self._stop_thread = False
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
		size_setting = Objects.settings.get_value('window-size')
		if isinstance(size_setting[1], int):
			self.set_property('height-request', size_setting[1]*0.7)
		else:
			self.set_property('height-request', 600)
		Gtk.Popover.do_show(self)
		self._text_entry.grab_focus()

	"""
		Remove row not existing in view, thread safe
	"""
	def _clear(self, results):
		length = len(results)
		for child in self._view.get_children():
			if length == 0 or not child._exists(results):
				GLib.idle_add(child.destroy)

	"""
		Return True if item exist in rows
		@param: item as SearchObject
	"""
	def _exists(self, item):
		found = False
		for child in self._view.get_children():
			if item.is_track and child.is_track:
				if item.id == child.id:
					found = True
					break
			elif not item.is_track and not child.is_track:
				if item.id == child.id:
					found = True
					break
		return found

	"""
		Timeout filtering, call _really_do_filterting() after a small timeout
	"""	
	def _do_filtering(self, data = None):
		if self._in_thread:
			self._stop_thread = True
			GLib.timeout_add(100, self._do_filtering)

		if self._text_entry.get_text() != "":
			if self._timeout:
				GLib.source_remove(self._timeout)
			self._timeout = GLib.timeout_add(100, self._do_filtering_thread)
		else:
			if self._timeout:
				GLib.source_remove(self._timeout)
			self._clear([])

	"""
		Just run _really_do_filtering in a thread
	"""
	def _do_filtering_thread(self):
		self._timeout = None
		self._in_thread = True
		start_new_thread(self._really_do_filtering, ())

	"""
		Populate treeview searching items in db based on text entry current text
	"""
	def _really_do_filtering(self):
		sql = Objects.db.get_cursor()
		results = []
		albums = []

		searched = self._text_entry.get_text()

		tracks_non_performer = []
		
		for artist_id in Objects.artists.search(searched, sql):
			for album_id in Objects.albums.get_ids(artist_id, None, sql):
				if (album_id, artist_id) not in albums:
					albums.append((album_id, artist_id))
			for track_id, track_name in Objects.tracks.get_as_non_performer(artist_id, sql):
				tracks_non_performer.append((track_id, track_name))

		albums += Objects.albums.search(searched, sql)

		for album_id, artist_id in albums:
			search_obj = SearchObject()
			search_obj.artist = Objects.artists.get_name(artist_id, sql)
			search_obj.title = Objects.albums.get_name(album_id, sql)
			search_obj.count = Objects.albums.get_count(album_id, sql)
			search_obj.id = album_id
			search_obj.album_id = album_id
			results.append(search_obj)

		for track_id, track_name in Objects.tracks.search(searched, sql)+tracks_non_performer:
			artist_id = Objects.tracks.get_artist_id(track_id, sql)
			search_obj = SearchObject()
			search_obj.artist = Objects.artists.get_name(artist_id, sql)
			search_obj.title = track_name
			search_obj.id = track_id
			search_obj.album_id = Objects.tracks.get_album_id(track_id, sql)
			search_obj.is_track = True
			results.append(search_obj)

		if not self._stop_thread:
			self._clear(results)
			GLib.idle_add(self._add_rows, results)
		else:
			self._in_thread = False
			self._stop_thread = False
			
	"""
		Add a rows recursively
		@param results as array of SearchObject
	"""
	def _add_rows(self, results):
		if len(results) > 0:
			result = results.pop(0)
			if not self._exists(result):
				search_row = SearchRow()
				search_row.set_artist(result.artist)
				if result.count != -1:
					result.title += " (%s)" % result.count
				search_row.set_title(result.title)
				search_row.set_cover(Objects.art.get(result.album_id, ART_SIZE_MEDIUM))
				search_row.id = result.id
				search_row.is_track = result.is_track
				self._view.add(search_row)
			if self._stop_thread:
				self._in_thread = False
				self._stop_thread = False
			else:
				GLib.idle_add(self._add_rows, results)
		else:
			self._in_thread = False
			self._stop_thread = False

	"""
		Play searched item when selected
		If item is an album, play first track
	"""
	def _on_activate(self, widget, row):
		value_id = row.id
		if row.is_track:
			Objects.player.load(value_id)
		else:
			genre_id = Objects.albums.get_genre_id(value_id)
			# Get first track from album
			track_id = Objects.albums.get_tracks(value_id)[0]
			Objects.player.load(track_id)
			if not Objects.player.is_party():
				album_id = Objects.tracks.get_album_id(track_id)
				Objects.player.set_album(album_id)


