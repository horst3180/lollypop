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

from gi.repository import GObject, Gtk, GLib, GdkPixbuf, Pango
from cgi import escape

from lollypop.config import *
from lollypop.albumart import AlbumArt
from lollypop.popmenu import PopMenu
from lollypop.utils import translate_artist_name, seconds_to_string

class TrackRow(Gtk.ListBoxRow):
	"""
		Init row widgets
	"""
	def __init__(self):
		Gtk.ListBoxRow.__init__(self)
		self._object_id = None
		self._num = 0
		self._number = 0
		self._menu_visible = False
		self._ui = Gtk.Builder()
		self._ui.add_from_resource('/org/gnome/Lollypop/TrackRow.ui')
		self._row_widget = self._ui.get_object('row')
		self._ui.get_object('menu').connect('clicked', self._pop_menu)
		self.add(self._row_widget)
		self.get_style_context().add_class('trackrow')
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
		Show play icon
		@param widget name as str
		@param show as bool
	"""
	def show_widget(self, name, show):
		widget = self._ui.get_object(name)
		if name == "icon":
			if show:
				widget.set_from_icon_name('media-playback-start-symbolic', 1)
				self.get_style_context().remove_class('trackrow')
				self.get_style_context().add_class('trackrowplaying')
			else:
				widget.clear()
				self.get_style_context().remove_class('trackrowplaying')
				self.get_style_context().add_class('trackrow')
		else:
			if show:
				widget.show()
			else:
				widget.hide()

	"""
		Set object label
		@param object as string
		@param label as string
	"""
	def set_label(self, obj, label):
		self._ui.get_object(obj).set_markup(label)

	"""
		Get object label
	"""
	def get_label(self, obj):
		return self._ui.get_object(obj).get_text()
		
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
		Set track number
		@param num as int
	"""
	def set_number(self, num):
		self._number = num
		
	"""
		Get track number
		@return num as int
	"""
	def get_number(self):
		return self._number
		
	"""
		Return True if menu is visible
		@return bool
	"""
	def is_menu_visible(self):
		return self._menu_visible

#######################
# PRIVATE             #
#######################
	"""
		Popup menu for track
		@param widget as Gtk.Button
	"""
	def _pop_menu(self, widget):
		self._menu_visible = True
		menu = PopMenu(self._object_id, False)
		popover = Gtk.Popover.new_from_model(self._ui.get_object('menu'), menu)
		popover.connect("closed", self._on_pop_closed)
		popover.show()

	"""
		Mark menu as not visible
		@param widget as Gtk.Popover
	"""
	def _on_pop_closed(self, widget):
		self._menu_visible = False

######################################################################
######################################################################

class TracksWidget(Gtk.ListBox):

	__gsignals__ = {
        'activated': (GObject.SIGNAL_RUN_FIRST, None, (int,))
    }

	def __init__(self, popover):
		Gtk.ListBox.__init__(self)
		self._popover = popover
		self.connect("row-activated", self._on_activate)
		self.get_style_context().add_class('trackswidget')

	"""
		Add track to list
		@param track id as int
		@param track number as int
		@param title as str
		@param length as str
		@param pos as int
	"""
	def add_track(self, track_id, num, title, length, pos):
		track_row = TrackRow()
		if not self._popover:
			track_row.show_widget('menu', False)
		if Objects["player"].get_current_track_id() == track_id:
			track_row.show_widget('icon', True)
		if pos:
			track_row.set_label('num', '''<span foreground="#72729f9fcfcf" font_desc="Bold">%s</span>''' % str(pos))
		else:
			track_row.set_label('num', str(num))
		track_row.set_number(num)
		track_row.set_label('title', escape(title))
		track_row.set_label('duration', seconds_to_string(length))
		track_row.set_object_id(track_id)
		track_row.show()
		self.add(track_row)

	"""
		Update playing track
		@param track id as int
	"""
	def update_playing(self, track_id):
		for row in self.get_children():
			if row.get_object_id() == track_id:
				row.show_widget('icon', True)
			else:
				row.show_widget('icon', False)


	"""
		Set signals callback
	"""
	def do_show(self):
		Objects["player"].connect("waitlist-changed", self._update_pos_label)
		Gtk.ListBox.do_show(self)
	
	"""
		Clean signals callback
	"""
	def do_hide(self):	
		Objects["player"].disconnect_by_func(self._update_pos_label)
		Gtk.ListBox.do_hide(self)
		
#######################
# PRIVATE             #
#######################
	"""
		Update position label
		@param player
		@param track id as int
	"""
	def _update_pos_label(self, widget):
		for row in self.get_children():
			track_id = row.get_object_id()
			if Objects["player"].is_in_waitlist(track_id):
				pos = Objects["player"].get_track_position(track_id)
				row.set_label('num', '''<span foreground="#72729f9fcfcf" font_desc="Bold">%s</span>''' % str(pos))
			else:
				row.set_label('num', str(row.get_number()))
	
	"""
		Play activated item
		@param widget as TracksWidget
		@param row as TrackRow
	"""
	def _on_activate(self, widget, row):
		self.emit('activated', row.get_object_id())
		
