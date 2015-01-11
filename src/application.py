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

from gi.repository import Gtk, Gio, GLib, Gdk, Notify
from gettext import gettext as _
from os import environ

from lollypop.define import Objects
from lollypop.window import Window
from lollypop.database import Database
from lollypop.player import Player
from lollypop.albumart import AlbumArt
from lollypop.widgets import ChooserWidget
from lollypop.mpris import MPRIS
from lollypop.notification import NotificationManager
from lollypop.database_albums import DatabaseAlbums
from lollypop.database_artists import DatabaseArtists
from lollypop.database_genres import DatabaseGenres
from lollypop.database_tracks import DatabaseTracks



class Application(Gtk.Application):

	"""
		Create application with a custom css provider
	"""
	def __init__(self):
		Gtk.Application.__init__(self,
					 application_id='org.gnome.Lollypop',
					 flags=Gio.ApplicationFlags.FLAGS_NONE)
		GLib.set_application_name('lollypop')
		GLib.set_prgname('lollypop')
		cssProviderFile = Gio.File.new_for_uri('resource:///org/gnome/Lollypop/application.css')
		cssProvider = Gtk.CssProvider()
		cssProvider.load_from_file(cssProviderFile)
		screen = Gdk.Screen.get_default()
		styleContext = Gtk.StyleContext()
		styleContext.add_provider_for_screen(screen, cssProvider,
						     Gtk.STYLE_PROVIDER_PRIORITY_USER)

		Objects.settings = Gio.Settings.new('org.gnome.Lollypop')
		Objects.db = Database()
		# We store a cursor for the main thread
		Objects.sql = Objects.db.get_cursor()
		Objects.albums = DatabaseAlbums()
		Objects.artists = DatabaseArtists()
		Objects.genres = DatabaseGenres()
		Objects.tracks = DatabaseTracks()	
		Objects.player = Player()
		Objects.art = AlbumArt()

		self.add_action(Objects.settings.create_action('shuffle'))
		self._window = None
		self._settings_dialog = None

		DESKTOP = environ.get("XDG_CURRENT_DESKTOP")
		if DESKTOP and "GNOME" in DESKTOP:
			self._appmenu = True
		else:
			self._appmenu = False

		self.register(None)
		if self.get_is_remote():
			Gdk.notify_startup_complete()
		
	"""
		Add startup notification and build gnome-shell menu after Gtk.Application startup
	"""
	def do_startup(self):
		Gtk.Application.do_startup(self)
		Notify.init("Lollypop")
		if self._appmenu:
			menu = self._setup_app_menu()
			self.set_app_menu(menu)

	"""
		Activate window and create it if missing
	"""
	def do_activate(self):
		if not self._window:
			self._window = Window(self)
			self._service = MPRIS(self)
			self._notifications = NotificationManager()
			self._window.connect('delete-event', self._hide_on_delete)
			self._window.setup_view()

			if not self._appmenu:
				menu = self._setup_app_menu()
				self._window.setup_menu(menu)
		self._window.present()

	"""
		Destroy main window
	"""
	def quit(self, action=None, param=None):
		Objects.player.stop()
		Objects.sql.execute("VACUUM")
		Objects.sql.close()
		self._window.destroy()

#######################
# PRIVATE             #
#######################

################
# settings

	"""
		Dialog to let user choose available options
	"""
	def _edit_settings(self, action, param):
		if not self._window or self._settings_dialog:
			return
		self._choosers = []
		builder = Gtk.Builder()
		builder.add_from_resource('/org/gnome/Lollypop/SettingsDialog.ui')
		self._settings_dialog = builder.get_object('settings_dialog')
		self._settings_dialog.set_transient_for(self._window)
		self._settings_dialog.set_title(_("Configure lollypop"))
		switch_scan =  builder.get_object('switch_scan')
		switch_scan.set_state(Objects.settings.get_value('startup-scan'))
		switch_view = builder.get_object('switch_view')
		switch_view.set_state(Objects.settings.get_value('dark-view'))
		switch_background = builder.get_object('switch_background')
		switch_background.set_state(Objects.settings.get_value('background-mode'))
		close_button = builder.get_object('close_btn')
		switch_scan.connect('state-set', self._update_scan_setting)
		switch_view.connect('state-set', self._update_view_setting)
		switch_background.connect('state-set', self._update_background_setting)
		close_button.connect('clicked', self._edit_settings_close)
		main_chooser_box = builder.get_object('main_chooser_box')
		self._chooser_box = builder.get_object('chooser_box')
		party_grid = builder.get_object('party_grid')
		
		#
		# Music tab
		#
		dirs = []
		for directory in Objects.settings.get_value('music-path'):
			dirs.append(directory)
			
		# Main chooser
		self._main_chooser = ChooserWidget()
		image = Gtk.Image.new_from_icon_name("list-add-symbolic", Gtk.IconSize.MENU)
		self._main_chooser.set_icon(image)
		self._main_chooser.set_action(self._add_chooser)
		main_chooser_box.pack_start(self._main_chooser, False, True, 0)
		if len(dirs) > 0:
			path = dirs.pop(0)
		else:
			path = GLib.get_user_special_dir(GLib.USER_DIRECTORY_MUSIC)
		self._main_chooser.set_dir(path)
		
		# Others choosers	
		for directory in dirs:
				self._add_chooser(directory)				
		
		#	
		# Party mode tab
		#
		genres = Objects.genres.get_ids()
		genres.insert(0, (-1, "Populars"))
		ids = Objects.player.get_party_ids()
		i = 0
		x = 0
		for genre_id, genre in genres:
			label = Gtk.Label()
			label.set_property('margin-start', 10)
			label.set_property('halign', Gtk.Align.START)
			label.set_text(genre)
			switch = Gtk.Switch()
			if genre_id in ids:
				switch.set_state(True)
			switch.connect("state-set", self._party_switch_state, genre_id)
			party_grid.attach(label, x, i, 1, 1)
			party_grid.attach(switch, x+1, i, 1, 1)
			if x == 0:
				x += 2
			else:
				i += 1
				x = 0

		self._settings_dialog.show_all()

	"""
		Add a new chooser widget
		@param directory path as string
	"""
	def _add_chooser(self, directory = None):
		chooser = ChooserWidget()
		image = Gtk.Image.new_from_icon_name("list-remove-symbolic", Gtk.IconSize.MENU)
		chooser.set_icon(image)
		if directory:
			chooser.set_dir(directory)
		self._chooser_box.add(chooser)

	"""
		Update view setting
		@param widget as unused, state as widget state
	"""
	def _update_view_setting(self, widget, state):
		Objects.settings.set_value('dark-view',  GLib.Variant('b', state))
		if self._window:
			self._window.update_view_class(state)

	"""
		Update scan setting
		@param widget as unused, state as widget state
	"""
	def _update_scan_setting(self, widget, state):
		Objects.settings.set_value('startup-scan',  GLib.Variant('b', state))

	"""
		Update background mode setting
		@param widget as unused, state as widget state
	"""
	def _update_background_setting(self, widget, state):
		Objects.settings.set_value('background-mode',  GLib.Variant('b', state))

	"""
		Close edit party dialog
		@param unused
	"""
	def _edit_settings_close(self, widget):
		paths = []
		main_path = self._main_chooser.get_dir()
		choosers = self._chooser_box.get_children()
		if main_path == GLib.get_user_special_dir(GLib.USER_DIRECTORY_MUSIC) and len(choosers) == 0:
			paths = []
		else:
			paths.append(main_path)
			for chooser in choosers:
				path = chooser.get_dir()
				if path and not path in paths:
					paths.append(path)

		previous = Objects.settings.get_value('music-path')
		Objects.settings.set_value('music-path', GLib.Variant('as', paths))
		self._settings_dialog.hide()
		self._settings_dialog.destroy()
		self._settings_dialog = None
		if set(previous) != set(paths):
			self._window.update_db()

	"""
		Update party ids when use change a switch in dialog
		@param widget as unused, state as widget state, genre id as int
	"""
	def _party_switch_state(self, widget, state, genre_id):
		ids = Objects.player.get_party_ids()
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
		Objects.player.set_party_ids(ids)
		Objects.settings.set_value('party-ids',  GLib.Variant('ai', ids))

################
# End Settings
################

	"""
		Hide window
	"""
	def _hide_on_delete(self, widget, event):
		if not Objects.settings.get_value('background-mode'):
			Objects.player.stop()
			GLib.timeout_add(500, self.quit)
		return widget.hide_on_delete()

	"""
		Search for new music
	"""
	def _update_db(self, action = None, param = None):
		if self._window:
			self._window.update_db()

	"""
		Setup about dialog
	"""
	def _about(self, action, param):
        	builder = Gtk.Builder()
        	builder.add_from_resource('/org/gnome/Lollypop/AboutDialog.ui')
        	about = builder.get_object('about_dialog')
        	about.set_transient_for(self._window)
        	about.connect("response", self._about_response)
        	about.show()

	"""
		Destroy about dialog when closed
	"""
	def _about_response(self, dialog, response):
		dialog.destroy()

	"""
		Setup application menu
		@return menu as Gio.Menu
	"""
	def _setup_app_menu(self):
		builder = Gtk.Builder()

		builder.add_from_resource('/org/gnome/Lollypop/app-menu.ui')

		menu = builder.get_object('app-menu')

		#TODO: Remove this test later
		if Gtk.get_minor_version() > 12:
			settingsAction = Gio.SimpleAction.new('settings', None)
			settingsAction.connect('activate', self._edit_settings)
			self.add_action(settingsAction)

		updateAction = Gio.SimpleAction.new('update_db', None)
		updateAction.connect('activate', self._update_db)
		self.add_action(updateAction)

		aboutAction = Gio.SimpleAction.new('about', None)
		aboutAction.connect('activate', self._about)
		self.add_action(aboutAction)

		quitAction = Gio.SimpleAction.new('quit', None)
		quitAction.connect('activate', self.quit)
		self.add_action(quitAction)

		return menu
