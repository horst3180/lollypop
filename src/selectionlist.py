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

from gi.repository import Gtk, GObject, Pango

from lollypop.database import Database
from lollypop.utils import translate_artist_name
from lollypop.config import *

class SelectionList(GObject.GObject):

	__gsignals__ = {
		'item-selected': (GObject.SIGNAL_RUN_FIRST, None, (int,)),
	}

	"""
		Init Selection list ui
	"""
	def __init__(self, title, width):
		GObject.GObject.__init__(self)
		
		self._model = Gtk.ListStore(int, str)	
		self._model.set_sort_column_id(0, Gtk.SortType.ASCENDING)
		self._model.set_sort_func(0, self._sort_items)
		self._sort = False
		self._values = None

		self._view = Gtk.TreeView(self._model)
		self._view.connect('cursor-changed', self._new_item_selected)
		renderer = Gtk.CellRendererText()
		renderer.set_fixed_size(width, -1)
		renderer.set_property('ellipsize-set',True)
		renderer.set_property('ellipsize', Pango.EllipsizeMode.END)
		self._view.append_column(Gtk.TreeViewColumn(title, renderer, text=1))
		self._view.set_headers_visible(False)
		self._view.show()

		self.widget = Gtk.ScrolledWindow()
		self.widget.set_vexpand(True)
		self.widget.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
		self.widget.add(self._view)
	
	"""
		Populate view with values
		Translate string if is_artist = True
	"""	
	def populate(self, values, is_artist = False):
		self._model.clear()
		for (object_id, string) in values:
			if is_artist:
				string = translate_artist_name(string)
			self._model.append([object_id, string])
				
	
	"""
		Update view with values
		Setup a sort function on list
		Please  use populate in priority
	"""	
	def update(self, values, is_artist = False):
		for item in self._model:
			found = False
			for value in values:
				if item == value:
					found = True
			if not found:
				self._model.remove(item.iter)

		self._values = values
		for value in values:
			found = False
			for item in self._model:
				if item == value:
					found = True
			if not found:
				if is_artist:
					string = translate_artist_name(value[1])
				else:
					string = value[1]
				self._model.append([value[0], string])
		self._values = None

	"""
		Make treeview select first default item
	"""
	def select_first(self):
		iterator = self._model.get_iter("0")
		path = self._model.get_path(iterator)
		self._view.set_cursor(path, None, False)

#######################
# PRIVATE             #
#######################
	"""
		Sort model
	"""
	def _sort_items(self, model, itera, iterb, data):
		a = model.get_value(itera, 0)
		b = model.get_value(itera, 0)
		if not self._values:
			return b < a
		#print("sort")
		if a == POPULARS:
			return False
		elif a == ALL:
			if b == POPULARS:
				return True
			else:
				return False
		elif a == COMPILATIONS:
			if b == POPULARS or b == ALL:
				return True
			else:
				return False
		else:
			pos_a = 0
			for rowid, string in self._values:
				if rowid == a:
					break
				pos_a += 1
			pos_b = 0
			for rowid, string in self._values:
				if rowid == a:
					break
				pos_b += 1

			return pos_a < pos_b

	"""
		Forward "cursor-changed" as "item-selected" with item id as arg
	"""	
	def _new_item_selected(self, view):
		(path, column) = view.get_cursor()
		if path:
			iter = self._model.get_iter(path)
			if iter:
				self.emit('item-selected', self._model.get_value(iter, 0))

