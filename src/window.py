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

from gi.repository import Gtk, Gdk, Gio, GLib
from gettext import gettext as _, ngettext

from lollypop.config import Objects
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

		self._scanner = CollectionScanner(Objects["settings"].get_value('music-path'))
		self._scanner.connect("scan-finished", self._update_list_one)

		self._setup_window()				
		self._setup_view()

		self._setup_media_keys()

		party_settings = Objects["settings"].get_value('party-ids')
		ids = []
		for setting in party_settings:
			if isinstance(setting, int):
				ids.append(setting)	
		Objects["player"].set_party_ids(ids)
		
		self.connect("map-event", self._on_mapped_window)



	def edit_party(self):
		builder = Gtk.Builder()
		builder.add_from_resource('/org/gnome/Lollypop/PartyDialog.ui')
		self._party_dialog = builder.get_object('party_dialog')
		self._party_dialog.set_transient_for(self)
		self._party_dialog.set_title(_("Select what will be available in party mode"))
		party_button = builder.get_object('button1')
		party_button.connect("clicked", self._edit_party_close)
		scrolled = builder.get_object('scrolledwindow1')
		genres = Objects["genres"].get_ids()
		genres.insert(0, (-1, "Populars"))
		self._party_grid = Gtk.Grid()
		self._party_grid.set_orientation(Gtk.Orientation.VERTICAL)
		self._party_grid.set_property("column-spacing", 10)
		ids = Objects["player"].get_party_ids()
		i = 0
		x = 0
		for genre_id, genre in genres:
			label = Gtk.Label()
			label.set_text(genre)
			switch = Gtk.Switch()
			if genre_id in ids:
				switch.set_state(True)
			switch.connect("state-set", self._party_switch_state, genre_id)
			self._party_grid.attach(label, x, i, 1, 1)
			self._party_grid.attach(switch, x+1, i, 1, 1)
			if x == 0:
				x += 2
			else:
				i += 1
				x = 0
		scrolled.add(self._party_grid)
		self._party_dialog.show_all()

	"""
		Update music database
		Empty database if reinit True
	"""
	def update_db(self):
		self._list_one.widget.hide()
		self._list_two.widget.hide()
		self._box.remove(self._view)
		self._view = LoadingView()
		self._box.add(self._view)
		self._scanner.update()

############
# Private  #
############

	"""
		Update party ids when use change a switch in dialog
	"""
	def _party_switch_state(self, widget, state, genre_id):
		ids = Objects["player"].get_party_ids()
		if state:
			try:
				ids.append(genre_id)
			except:
				pass
		else:
			try:
				ids.remove(genre_id)
			except:
				pass
		Objects["player"].set_party_ids(ids)
		Objects["settings"].set_value('party-ids',  GLib.Variant('ai', ids))
		

	"""
		Close edit party dialog
	"""
	def _edit_party_close(self, widget):
		self._party_dialog.hide()
		self._party_dialog.destroy()

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
			Objects["player"].play_pause()
		elif 'Stop' in response:
			Objects["player"].stop()
		elif 'Next' in response:
			Objects["player"].next()
		elif 'Previous' in response:
			Objects["player"].prev()
	
	"""
		Setup window icon, position and size, callback for updating this values
	"""
	def _setup_window(self):
		self.set_size_request(200, 100)
		self.set_icon_name('lollypop')
		size_setting = Objects["settings"].get_value('window-size')
		if isinstance(size_setting[0], int) and isinstance(size_setting[1], int):
			self.resize(size_setting[0], size_setting[1])

		position_setting = Objects["settings"].get_value('window-position')
		if len(position_setting) == 2 \
			and isinstance(position_setting[0], int) \
			and isinstance(position_setting[1], int):
			self.move(position_setting[0], position_setting[1])

		if Objects["settings"].get_value('window-maximized'):
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
		self._box = Gtk.Grid()
		self._toolbar = Toolbar()
		self.set_titlebar(self._toolbar.header_bar)
		self._toolbar.header_bar.show()
		self._toolbar.get_infobox().connect("button-press-event", self._show_current_album)
		self._toolbar.get_view_genres_btn().connect("toggled", self._update_list_one)
		self._list_one = SelectionList("Genre", 150)
		self._list_two = SelectionList("Artist", 200)
		self._item_id = -1
		
		self._view = LoadingView()

		separator = Gtk.Separator()
		separator.show()
		self._box.add(self._list_one.widget)
		self._box.add(separator)
		self._box.add(self._list_two.widget)
		self._box.add(self._view)
		self.add(self._box)
		self._box.show()
		self.show()

	
	"""
		Run collection update on mapped window
		Pass _update_genre() as collection scanned callback
	"""	
	def _on_mapped_window(self, obj, data):
		if Objects["tracks"].is_empty():
			self._scanner.update()
		elif Objects["settings"].get_value('startup-scan'):
			self._scanner.update(True)
			self._init_list_one()
		else:
			self._init_list_one()
	
	"""
		Init the filter list
	"""
	def _init_main_list(self, widget):
		if self._list_one.widget.is_visible():
			self._update_genres()
		else:
			self._init_genres()
	"""
		Init list with genres or artist
	"""
	def _init_list_one(self):
		active = self._toolbar.get_view_genres_btn().get_active()
		if active:
			items = Objects["genres"].get_ids()
			self._list_one.connect('item-selected', self._init_list_two)
		else:
			items = Objects["artists"].get_ids()
			self._list_one.connect('item-selected', self._update_view_artists)

		items.insert(0, (-1, _("All artists")))
		items.insert(0, (-2, _("Populars albums")))
		self._list_one.populate(items, not active)	
		self._list_one.select_first()
		self._list_one.widget.show()

	"""
		Update with new genres or artist
	"""
	def _update_list_one(self, obj = None, data = None):
		previous = Objects["settings"].get_value('hide-genres')
		active = self._toolbar.get_view_genres_btn().get_active()
		if active:
			self._list_one.disconnect_by_func(self._update_view_artists)
			self._list_one.connect('item-selected', self._init_list_two)
			items = Objects["genres"].get_ids()
			
			
		
		else:
			self._item_id = None
			self._list_one.disconnect_by_func(self._init_list_two)
			self._list_one.connect('item-selected', self._update_view_artists)
			items = Objects["artists"].get_ids()
			self._list_two.widget.hide()

		items.insert(0, (-1, _("All artists")))
		items.insert(0, (-2, _("Populars albums")))
		self._list_one.update(items, not active)
		if previous != active:
			Objects["settings"].set_value('hide-genres', GLib.Variant('b', active))
			self._list_one.select_first()
		elif not self._list_one.widget.is_visible():
			self._list_one.select_first()
			self._list_one.widget.show()
	"""
		Init list two with artist based on genre
	"""
	def _init_list_two(self, obj, genre_id):
		try:
			self._list_two.disconnect_by_func(self._update_view_artist)
		except:
			pass
		self._item_id = genre_id
		if genre_id == -1:
			values = Objects["artists"].get_ids()
			if len(Objects["albums"].get_compilations()) > 0:
				values.insert(0, (-1, _("Compilations")))
			self._list_two.populate(values, True)
			self._update_view_albums()
			self._list_two.widget.show()
		elif genre_id == -2:
			self._update_view_populars_albums()
			self._list_two.widget.hide()
		else:
			values = Objects["artists"].get_ids(genre_id)
			if len(Objects["albums"].get_compilations(genre_id)) > 0:
				values.insert(0, (-1, _("Compilations")))
			self._list_two.populate(values, True)
			self._update_view_albums()
			self._list_two.widget.show()
		self._list_two.connect('item-selected', self._update_view_artists)


	"""
		Update artist view for artist_id
	"""
	def _update_view_artists(self, obj, artist_id):
		if artist_id == -1:
			self._update_view_albums()
		elif artist_id == -2:
			self._update_view_populars_albums()
		else:
			self._box.remove(self._view)
			self._view.destroy()
			self._view = ArtistView(artist_id, self._item_id)
			self._box.add(self._view)
			self._view.populate()
	
	"""
		Update albums view with populars albums
	"""
	def _update_view_populars_albums(self):
		self._box.remove(self._view)
		self._view.remove_signals()
		self._view = AlbumView(self._item_id)
		self._box.add(self._view)
		self._view.populate_popular()
	"""
		Update albums view for genre_id
	"""
	def _update_view_albums(self):
		self._box.remove(self._view)
		self._view.remove_signals()
		self._view = AlbumView(self._item_id)
		self._box.add(self._view)
		self._view.populate()
	
	"""
		Save new window size/position
	"""		
	def _on_configure_event(self, widget, event):
		size = widget.get_size()
		Objects["settings"].set_value('window-size', GLib.Variant('ai', [size[0], size[1]]))

		position = widget.get_position()
		Objects["settings"].set_value('window-position', GLib.Variant('ai', [position[0], position[1]]))

	"""
		Save maximised state
	"""
	def _on_window_state_event(self, widget, event):
		Objects["settings"].set_boolean('window-maximized', 'GDK_WINDOW_STATE_MAXIMIZED' in event.new_window_state.value_names)

	"""
		Show current album context/content
	"""
	def _show_current_album(self, obj, data):
		track_id = Objects["player"].get_current_track_id()
		if  track_id != -1:
			self._view.current_changed(False, track_id)


