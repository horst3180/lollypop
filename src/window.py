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
from lollypop.playlists import PlaylistsManager
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
		# SelectionList::update() is based on index in values tuple. For db objects, it's rowid so
		# it will works. For playlists, we just use a static int and increment it over time
		self._counter = 0
		# Playlist do not have id (not in db), so we use an index to retrieve playlist name
		self._playlists = []

		self._setup_window()				
		self._setup_view()

		if not self._setup_scanner():
			if Objects.settings.get_value('save-state'):
				self._restore_view_state()
			else:
				self._list_one.select_item(0)

		self._setup_media_keys()

		party_settings = Objects.settings.get_value('party-ids')
		ids = []
		for setting in party_settings:
			if isinstance(setting, int):
				ids.append(setting)	
		Objects.player.set_party_ids(ids)
		self.connect("destroy", self._on_destroyed_window)
		Objects.playlists.connect("playlists-changed", self._update_lists)
		Objects.playlists.connect("playlist-changed", self._on_playlist_changed)

	"""
		Update music database
	"""
	def update_db(self):
		self._list_one.widget.hide()
		self._list_two.widget.hide()

		old_view = self._stack.get_visible_child()
		view = LoadingView()
		self._stack.add(view)
		self._stack.set_visible_child(view)
		self.save_view_state()
		self._scanner.update(self._progress, False)

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

	"""
		Save view state
	"""
	def save_view_state(self):
		Objects.settings.set_value("list-one", GLib.Variant('i', self._list_one.get_selected_item()))
		Objects.settings.set_value("list-two", GLib.Variant('i', self._list_two.get_selected_item()))

############
# Private  #
############
	"""
		Restore saved view
	"""
	def _restore_view_state(self):
		position = Objects.settings.get_value('list-one').get_int32()
		if position != -1:
			self._list_one.select_item(position)
		position = Objects.settings.get_value('list-two').get_int32()
		if position != -1:
			self._list_two.select_item(position)

	"""
		Run collection update if needed
		@return True if hard scan is running
	"""	
	def _setup_scanner(self):
		self._scanner = CollectionScanner()
		self._scanner.connect("scan-finished", self._update_lists)

		if Objects.tracks.is_empty():
			self._scanner.update(self._progress, False)
			return True
		elif Objects.settings.get_value('startup-scan'):
			self._scanner.update(self._progress, True)
			return False

	"""
		Update lists
		@param updater as GObject
	"""
	def _update_lists(self, updater):
		if self._list_one.length() > 0:
			self._update_list_one(updater)
			self._list_one.widget.show()
		if self._list_two.length() > 0:
			self._update_list_two(updater)
			self._list_two.widget.show()
		if isinstance(updater, CollectionScanner):
			view = self._stack.get_visible_child()
			if isinstance(view, LoadingView):
				view.destroy()

	"""
		Update list one
		@param updater as GObject
	"""
	def _update_list_one(self, updater):
		# Do not update if updater is PlaylistsManager
		if not isinstance(updater, PlaylistsManager):
			self._setup_lists(True)
		
	"""
		Update list two
		@param updater as GObject
	"""
	def _update_list_two(self, updater):
		object_id = self._list_one.get_selected_id()
		if (isinstance(updater, PlaylistsManager) and object_id == PLAYLISTS) or \
		   (isinstance(updater, CollectionScanner) and object_id != PLAYLISTS):		
			self._setup_list_artists(self._list_two, object_id, True)

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
		self._toolbar.get_view_genres_btn().connect("toggled", self._on_genres_btn_toggled)
		self._show_genres = self._toolbar.get_view_genres_btn().get_active()

		self._list_one = SelectionList()
		self._list_two = SelectionList()
		self._list_one.connect('item-selected', self._on_list_one_selected)
		self._list_two.connect('item-selected', self._on_list_two_selected)
		self._list_one.widget.show()
		self._setup_lists(False)
		
		loading_view = LoadingView()

		self._stack = Gtk.Stack()
		self._stack.add(loading_view)
		self._stack.set_visible_child(loading_view)
		self._stack.set_transition_duration(500)
		self._stack.set_property('expand', True)
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

	"""
		Return list one headers
	"""
	def _get_headers(self):
		items = []
		items.append((POPULARS, _("Popular albums")))
		items.append((PLAYLISTS, _("Playlists")))
		items.append((ALL, _("All artists")))
		return items
		
	"""
		Setup genres/artists lists
		@param update as bool, if True, just update entries
	"""
	def _setup_lists(self, update):
		if self._show_genres:
			self._setup_list_genres(self._list_one, update)
		else:
			self._setup_list_artists(self._list_one, ALL, update)

	"""
		Setup list for genres
		@param list as SelectionList
		@param update as bool, if True, just update entries
	"""
	def _setup_list_genres(self, selection_list, update):
		selection_list.mark_as_artists(False)
		items = self._get_headers() + Objects.genres.get()
		if update:
			selection_list.update(items)
		else:
			selection_list.populate(items)

	"""
		Setup list for artists
		@param list as SelectionList
		@param update as bool, if True, just update entries
	"""
	def _setup_list_artists(self, selection_list, genre_id, update):
		if selection_list == self._list_one and self._list_two.widget.is_visible():
			self._list_two.widget.hide()
			self._list_two.clear()
			
		items = []
		selection_list.mark_as_artists(True)
		if selection_list == self._list_one:
			items = self._get_headers()
		if len(Objects.albums.get_compilations(genre_id)) > 0:
			items.append((COMPILATIONS, _("Compilations")))
			
		items += Objects.artists.get(genre_id)
		
		if update:
			selection_list.update(items)
		else:
			selection_list.populate(items)

	"""
		Setup list for playlists
		@param update as bool
	"""
	def _setup_list_playlists(self, update):
		self._playlists = []
		self._clear_list(self._list_two, self._on_list_two_selected)
		self._list_two.mark_as_artists(False)
		playlist_names = Objects.playlists.get()
		for playlist_name in playlist_names:
			self._playlists.append((self._counter, playlist_name))
			self._counter += 1
		values = self._playlists
	
		# Do not show list if empty
		if len(values) > 0:
			if update:
				self._list_two.update(values)
			else:
				self._list_two.populate(values)

		# Only update view on list populate
		if not update:
			self._update_view_playlists(None)

	"""
		Update detailed view
		@param object id as int
		@param genre id as int
	"""
	def _update_view_detailed(self, object_id, genre_id):
		if genre_id == PLAYLISTS:
			self._update_view_playlists(object_id)
		elif object_id == ALL or object_id == POPULARS:
			self._update_view_genres(object_id)
		else:
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
		playlist_name = None
		old_view = self._stack.get_visible_child()

		if playlist_id != None:
			for item in self._playlists:
				if item[0] == playlist_id:
					playlist_name = item[1]
					break
		if playlist_name:
			view = PlaylistView(playlist_name)
		else:
			view = PlaylistConfigureView()

		view.show()
		self._stack.add(view)
		self._stack.set_visible_child(view)
		start_new_thread(view.populate, ())
		self._clean_view(old_view)

	"""
		Clear selection list
		@param selection list as SelectionList
		@param callback associated to selection list
	"""
	def _clear_list(self, selection_list, callback):
		selection_list.disconnect_by_func(callback)
		selection_list.clear()
		selection_list.connect('item-selected', callback)
		
	"""
		Clean view
		@param view as View
	"""
	def _clean_view(self, view):
		if view:
			view.stop()
			self._stack.remove(view)
			view.remove_signals()
			view.destroy()
	
	"""
		Update view based on selected object
		@param list as SelectionList
		@param object id as int
	"""
	def _on_list_one_selected(self, selection_list, object_id):
		if object_id == PLAYLISTS:
			self._setup_list_playlists(False)
			self._list_two.widget.show()
		elif selection_list.is_marked_as_artists():
			self._list_two.widget.hide()
			self._list_two.clear()
			self._update_view_detailed(object_id, None)
		else:
			if object_id == POPULARS:
				self._list_two.widget.hide()
				self._list_two.clear()
			else:
				self._clear_list(self._list_two, self._on_list_two_selected)
				self._setup_list_artists(self._list_two, object_id, False)
				self._list_two.widget.show()
			self._update_view_genres(object_id)

	"""
		Update view based on selected object
		@param list as SelectionList
		@param object id as int
	"""
	def _on_list_two_selected(self, selection_list, object_id):
		if self._list_one.get_selected_id() == PLAYLISTS:
			self._update_view_playlists(object_id)
		else:
			self._update_view_detailed(object_id, None)

	"""
		On genres button toggled, update lists/views
	"""
	def _on_genres_btn_toggled(self, button):
		self._show_genres = self._toolbar.get_view_genres_btn().get_active()
		self._clear_list(self._list_one, self._on_list_one_selected)
		self._setup_lists(False)
		
	"""
		Update playlist view if we are in playlist view
		@param manager as PlaylistPopup
		@param playlist name as str
	"""
	def _on_playlist_changed(self, manager, playlist_name):
		old_view = self._stack.get_visible_child()
		if isinstance(old_view, PlaylistView):
			old_name = old_view.get_name()
			if old_name == playlist_name:
				view = PlaylistView(old_name)
				view.show()
				self._stack.add(view)
				self._stack.set_visible_child(view)
				start_new_thread(view.populate, ())
				self._clean_view(old_view)

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
	
