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

from gi.repository import Gtk, Gdk, Gio, GLib
from gettext import gettext as _, ngettext
from _thread import start_new_thread
from os import environ

from lollypop.define import Objects
from lollypop.collectionscanner import CollectionScanner
from lollypop.toolbar import Toolbar
from lollypop.database import Database
from lollypop.selectionlist import SelectionList
from lollypop.player import Player
from lollypop.view import *

class Window(Gtk.ApplicationWindow):

	"""
		Init window objects
	"""	
	def __init__(self, app):
		Gtk.ApplicationWindow.__init__(self,
					       application=app,
					       title=_("Lollypop"))

		self._timeout = None
		self._scanner = CollectionScanner()
		self._scanner.connect("scan-finished", self._setup_list_one, True)

		self._setup_window()				
		self._setup_view()

		self._setup_media_keys()

		party_settings = Objects.settings.get_value('party-ids')
		ids = []
		for setting in party_settings:
			if isinstance(setting, int):
				ids.append(setting)	
		Objects.player.set_party_ids(ids)
		self.connect("destroy", self._on_destroyed_window)

	"""
		Run collection update if needed
	"""	
	def setup_view(self):
		if Objects.tracks.is_empty():
			self._scanner.update(self._progress, False)
			return
		elif Objects.settings.get_value('startup-scan'):
			self._scanner.update(self._progress, True)
			
		self._setup_list_one()
		self._update_view_genres(POPULARS)

	"""
		Update music database
	"""
	def update_db(self):
		self._list_one.widget.hide()
		self._list_two.widget.hide()

		old_view = self._stack.get_visible_child()		
		self._loading = True
		view = LoadingView()
		self._stack.add(view)
		self._stack.set_visible_child(view)
		self._scanner.update(self._progress, False)
		if old_view:
			self._stack.remove(old_view)
			old_view.remove_signals()


	"""
		Update view class
		@param bool
	"""
	def update_view_class(self, dark):
		current_view = self._stack.get_visible_child()
		if dark:
			current_view.get_style_context().add_class('black')
		else:
			current_view.get_style_context().remove_class('black')

	"""
		Add an application menu to window
		@parma: menu as Gio.Menu
	"""
	def setup_menu(self, menu):
		self._toolbar.setup_menu_btn(menu)

############
# Private  #
############

	"""
		Setup media player keys
	"""
	def _setup_media_keys(self):
		self._proxy = Gio.DBusProxy.new_sync(Gio.bus_get_sync(Gio.BusType.SESSION, None),
											 Gio.DBusProxyFlags.NONE,
											 None,
											 'org.gnome.SettingsDaemon',
											 '/org/gnome/SettingsDaemon/MediaKeys',
											 'org.gnome.SettingsDaemon.MediaKeys',
											 None)
		self._grab_media_player_keys()
		try:
			self._proxy.connect('g-signal', self._handle_media_keys)
		except GLib.GError:
            # We cannot grab media keys if no settings daemon is running
			pass

	"""
		Do key grabbing
	"""
	def _grab_media_player_keys(self):
		try:
			self._proxy.call_sync('GrabMediaPlayerKeys',
								 GLib.Variant('(su)', ('Lollypop', 0)),
								 Gio.DBusCallFlags.NONE,
								 -1,
								 None)
		except GLib.GError:
			# We cannot grab media keys if no settings daemon is running
			pass

	"""
		Do player actions in response to media key pressed
	"""
	def _handle_media_keys(self, proxy, sender, signal, parameters):
		if signal != 'MediaPlayerKeyPressed':
			print('Received an unexpected signal \'%s\' from media player'.format(signal))
			return
		response = parameters.get_child_value(1).get_string()
		if 'Play' in response:
			Objects.player.play_pause()
		elif 'Stop' in response:
			Objects.player.stop()
		elif 'Next' in response:
			Objects.player.next()
		elif 'Previous' in response:
			Objects.player.prev()
	
	"""
		Setup window icon, position and size, callback for updating this values
	"""
	def _setup_window(self):
		self.set_icon_name('lollypop')
		size_setting = Objects.settings.get_value('window-size')
		if isinstance(size_setting[0], int) and isinstance(size_setting[1], int):
			self.resize(size_setting[0], size_setting[1])
		else:
			self.set_size_request(800, 600)
		position_setting = Objects.settings.get_value('window-position')
		if len(position_setting) == 2 \
			and isinstance(position_setting[0], int) \
			and isinstance(position_setting[1], int):
			self.move(position_setting[0], position_setting[1])

		if Objects.settings.get_value('window-maximized'):
			self.maximize()

		self.connect("window-state-event", self._on_window_state_event)
		self.connect("configure-event", self._on_configure_event)

	"""
		Setup window main view:
			- genre list
			- artist list
			- main view as artist view or album view
	"""
	def _setup_view(self):
		self._paned_main_list = Gtk.HPaned()
		self._paned_list_view = Gtk.HPaned()
		vgrid = Gtk.Grid()
		vgrid.set_orientation(Gtk.Orientation.VERTICAL)
	
		self._toolbar = Toolbar()
		self._toolbar.header_bar.show()
		self._toolbar.get_view_genres_btn().connect("toggled", self._setup_list_one)

		self._list_one = SelectionList("Genre")
		self._list_two = SelectionList("Artist")
		self._list_one_signal = None
		self._list_two_signal = None
		
		self._loading = True
		loading_view = LoadingView()

		self._stack = Gtk.Stack()
		self._stack.add(loading_view)
		self._stack.set_visible_child(loading_view)
		self._stack.set_transition_duration(500)
		self._stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
		self._stack.show()

		self._progress = Gtk.ProgressBar()

		vgrid.add(self._stack)
		vgrid.add(self._progress)
		vgrid.show()

		# Only set headerbar on Gnome Shell and Pantheon Shell
		DESKTOP = environ.get("XDG_CURRENT_DESKTOP")
		if DESKTOP and ("GNOME" in DESKTOP or "Pantheon" in DESKTOP):
			self.set_titlebar(self._toolbar.header_bar)
			self._toolbar.header_bar.set_show_close_button(True)
			self.add(self._paned_main_list)
		else:
			hgrid = Gtk.Grid()
			hgrid.set_orientation(Gtk.Orientation.VERTICAL)
			hgrid.add(self._toolbar.header_bar)
			hgrid.add(self._paned_main_list)
			hgrid.show()
			self.add(hgrid)

		separator = Gtk.Separator()
		separator.show()
		self._paned_list_view.add1(self._list_two.widget)
		self._paned_list_view.add2(vgrid)
		self._paned_main_list.add1(self._list_one.widget)
		self._paned_main_list.add2(self._paned_list_view)
		self._paned_main_list.set_position(Objects.settings.get_value("paned-mainlist-width").get_int32())
		self._paned_list_view.set_position(Objects.settings.get_value("paned-listview-width").get_int32())
		self._paned_main_list.show()
		self._paned_list_view.show()
		self.show()

	"""
		Init the filter list
		@param widget as unused
	"""
	def _init_main_list(self, widget):
		if self._list_one.widget.is_visible():
			self._update_genres()
		else:
			self._init_genres()
	"""
		Init list with genres or artist
		If update, only update list content
		@param obj as unused, bool
	"""
	def _setup_list_one(self, obj = None, update = None):
		if self._list_one_signal:
			self._list_one.disconnect(self._list_one_signal)
		is_artist = not self._toolbar.get_view_genres_btn().get_active()

		# We show all artists
		if is_artist:
			self._list_two.widget.hide()
			items = Objects.artists.get(ALL)
			if len(Objects.albums.get_compilations(ALL)) > 0:
				items.insert(0, (COMPILATIONS, _("Compilations")))	
		# We show genres		
		else:
			items = Objects.genres.get()

		items.insert(0, (ALL, _("All artists")))
		items.insert(0, (PLAYLISTS, _("Playlists")))
		items.insert(0, (POPULARS, _("Popular albums")))

		if update:
			self._list_one.update(items, is_artist)
		else:
			self._list_one.populate(items, is_artist)		

		# If was empty
		if not self._list_one_signal:
			self._list_one.select_first()

		if self._loading:
			self._stack.get_visible_child().hide()
			self._list_one.select_first()
			self._update_view_genres(POPULARS)
			self._loading = False

		self._list_one.widget.show()
		if is_artist:
			self._list_one_signal = self._list_one.connect('item-selected', self._update_view_detailed, None)
		else:
			self._list_one_signal = self._list_one.connect('item-selected', self._setup_list_two)		

	"""
		Init list two with artist based on genre
		@param obj as unused, genre id as int
	"""
	def _setup_list_two(self, obj, genre_id):
		if self._list_two_signal:
			self._list_two.disconnect(self._list_two_signal)

		if genre_id == POPULARS:
			self._list_two.widget.hide()
			self._list_two_signal = None
		else:
			if genre_id == PLAYLISTS:
				values = Objects.playlists.get()
			else:
				values = Objects.artists.get(genre_id)
			if len(Objects.albums.get_compilations(genre_id)) > 0:
				values.insert(0, (COMPILATIONS, _("Compilations")))
			self._list_two.populate(values, True)
			self._list_two.widget.show()
			self._list_two_signal = self._list_two.connect('item-selected', self._update_view_detailed, genre_id)

		# In playlist mode, we do not show anything
		if genre_id == PLAYLISTS:
			old_view = self._stack.get_visible_child()
			self._clean_view(old_view)
		else:
			self._update_view_genres(genre_id)
			

	"""
		Update detailed view
		@param obj as SelectionList
		@param object id as int
		@param genre id as int
	"""
	def _update_view_detailed(self, obj, object_id, genre_id):
		is_artist = not self._toolbar.get_view_genres_btn().get_active()
		if object_id == PLAYLISTS:
			self._setup_list_two(obj, PLAYLISTS)
		elif genre_id == PLAYLISTS:
			self._update_view_playlists(object_id)
		elif object_id == ALL or object_id == POPULARS:
			if is_artist:
				self._list_two.widget.hide()
			self._update_view_genres(object_id)
		else:
			if is_artist:
				self._list_two.widget.hide()
			old_view = self._stack.get_visible_child()
			view = ArtistView(object_id, genre_id, True)
			self._stack.add(view)
			start_new_thread(view.populate, ())
			self._stack.set_visible_child(view)
			self._clean_view(old_view)

	"""
		Update albums view
		@param genre id as int
	"""
	def _update_view_genres(self, genre_id):
		old_view = self._stack.get_visible_child()
		view = AlbumView(genre_id)
		self._stack.add(view)
		start_new_thread(view.populate, ())
		self._stack.set_visible_child(view)
		self._clean_view(old_view)

	"""
		Update playlist view
		@param playlist id as int
	"""
	def _update_view_playlists(self, playlist_id):
		old_view = self._stack.get_visible_child()
		view = PlaylistView(playlist_id)
		self._stack.add(view)
		self._stack.set_visible_child(view)
		self._clean_view(old_view)
		
	"""
		Clean view
		@param view as View
	"""
	def _clean_view(self, view):
		if view:
			view.stop()
			self._stack.remove(view)
			view.remove_signals()

	"""
		Delay event
		@param: widget as Gtk.Window
		@param: event as Gtk.Event
	"""		
	def _on_configure_event(self, widget, event):
		if self._timeout:
			GLib.source_remove(self._timeout)
		self._timeout = GLib.timeout_add(500, self._save_size_position, widget)
	
	"""
		Save window state, update current view content size
		@param: widget as Gtk.Window
	"""
	def _save_size_position(self, widget):
		self._timeout = None
		size = widget.get_size()
		Objects.settings.set_value('window-size', GLib.Variant('ai', [size[0], size[1]]))
		position = widget.get_position()
		Objects.settings.set_value('window-position', GLib.Variant('ai', [position[0], position[1]]))

	"""
		Save maximised state
	"""
	def _on_window_state_event(self, widget, event):
		Objects.settings.set_boolean('window-maximized', 'GDK_WINDOW_STATE_MAXIMIZED' in event.new_window_state.value_names)

	"""
		Save paned widget width
		@param widget as unused, data as unused
	"""	
	def _on_destroyed_window(self, widget):
		Objects.settings.set_value("paned-mainlist-width", GLib.Variant('i', self._paned_main_list.get_position()))
		Objects.settings.set_value("paned-listview-width", GLib.Variant('i', self._paned_list_view.get_position()))
	
