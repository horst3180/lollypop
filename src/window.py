#!/usr/bin/python
# Copyright (c) 2014-2015 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from gi.repository import Gtk, Gio, GLib

import os

from lollypop.container import Container
from lollypop.define import Objects
from lollypop.toolbar import Toolbar


# Main window
class Window(Gtk.ApplicationWindow, Container):
    """
        Init window objects
    """
    def __init__(self, app):
        Container.__init__(self)
        Gtk.ApplicationWindow.__init__(self,
                                       application=app,
                                       title="Lollypop")
        
        self._timeout_configure = None

        self._setup_window()
        self._setup_media_keys()

        self.connect("destroy", self._on_destroyed_window)


    """
        Add an application menu to window
        @parma: menu as Gio.Menu
    """
    def setup_menu(self, menu):
        self._toolbar.setup_menu_btn(menu)

    """
        Setup media player keys
    """
    def _setup_media_keys(self):
        self._proxy = Gio.DBusProxy.new_sync(
                            Gio.bus_get_sync(Gio.BusType.SESSION, None),
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
            print('Received an unexpected signal\
                   \'%s\' from media player'.format(signal))
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
        if isinstance(size_setting[0], int) and\
           isinstance(size_setting[1], int):
            self.resize(size_setting[0], size_setting[1])
        else:
            self.set_size_request(800, 600)
        position_setting = Objects.settings.get_value('window-position')
        if len(position_setting) == 2 and\
           isinstance(position_setting[0], int) and\
           isinstance(position_setting[1], int):
            self.move(position_setting[0], position_setting[1])

        if Objects.settings.get_value('window-maximized'):
            self.maximize()

        self.connect("window-state-event", self._on_window_state_event)
        self.connect("configure-event", self._on_configure_event)

        self._toolbar = Toolbar(self.get_application())
        self._toolbar.header_bar.show()
        self._toolbar.get_view_genres_btn().connect(
                                            "toggled",
                                            self._on_genres_btn_toggled)
        self._show_genres = self._toolbar.get_view_genres_btn().get_active()

        # Only set headerbar on Gnome Shell and Pantheon Shell
        DESKTOP = os.environ.get("XDG_CURRENT_DESKTOP")
        if DESKTOP and ("GNOME" in DESKTOP or "Pantheon" in DESKTOP):
            self.set_titlebar(self._toolbar.header_bar)
            self._toolbar.header_bar.set_show_close_button(True)
            self.add(self.main_widget())
        else:
            hgrid = Gtk.Grid()
            hgrid.set_orientation(Gtk.Orientation.VERTICAL)
            hgrid.add(self._toolbar.header_bar)
            hgrid.add(self.main_widget())
            hgrid.show()
            self.add(hgrid)

    """
        On genres button toggled, update lists/views
    """
    def _on_genres_btn_toggled(self, button):
        self._show_genres = self._toolbar.get_view_genres_btn().get_active()
        self._setup_lists(False)

    """
        Delay event
        @param: widget as Gtk.Window
        @param: event as Gtk.Event
    """
    def _on_configure_event(self, widget, event):
        if self._timeout_configure:
            GLib.source_remove(self._timeout_configure)
        self._timeout_configure = GLib.timeout_add(500,
                                                   self._save_size_position,
                                                   widget)

    """
        Save window state, update current view content size
        @param: widget as Gtk.Window
    """
    def _save_size_position(self, widget):
        self._timeout_configure = None
        size = widget.get_size()
        Objects.settings.set_value('window-size',
                                   GLib.Variant('ai',
                                                [size[0], size[1]]))

        position = widget.get_position()
        Objects.settings.set_value('window-position',
                                   GLib.Variant('ai',
                                                [position[0], position[1]]))

    """
        Save maximised state
    """
    def _on_window_state_event(self, widget, event):
        Objects.settings.set_boolean('window-maximized',
                                     'GDK_WINDOW_STATE_MAXIMIZED' in
                                     event.new_window_state.value_names)

    """
        Save paned widget width
        @param widget as unused, data as unused
    """
    def _on_destroyed_window(self, widget):
        Objects.settings.set_value("paned-mainlist-width",
                                   GLib.Variant(
                                        'i',
                                        self._paned_main_list.get_position()))
        Objects.settings.set_value("paned-listview-width",
                                   GLib.Variant(
                                        'i',
                                        self._paned_list_view.get_position()))
