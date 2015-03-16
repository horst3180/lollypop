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

from gi.repository import Gtk, GLib
from gettext import gettext as _

from lollypop.define import Objects


# Dialog showing lollypop options
class SettingsDialog(Gtk.Dialog):

    def __init__(self, parent):

        self._choosers = []
        self._window = parent

        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/SettingsDialog.ui')

        self._settings_dialog = builder.get_object('settings_dialog')
        self._settings_dialog.set_transient_for(parent)
        self._settings_dialog.set_title(_("Configure lollypop"))

        switch_scan = builder.get_object('switch_scan')
        switch_scan.set_state(Objects.settings.get_value('startup-scan'))
        switch_scan.connect('state-set', self._update_scan_setting)

        switch_view = builder.get_object('switch_dark')
        switch_view.set_state(Objects.settings.get_value('dark-ui'))
        switch_view.connect('state-set', self._update_ui_setting)

        switch_background = builder.get_object('switch_background')
        switch_background.set_state(Objects.settings.get_value(
                                                    'background-mode'))
        switch_background.connect('state-set',
                                  self._update_background_setting)

        switch_state = builder.get_object('switch_state')
        switch_state.set_state(Objects.settings.get_value('save-state'))
        switch_state.connect('state-set', self._update_state_setting)

        switch_autoplay = builder.get_object('switch_autoplay')
        switch_autoplay.set_state(Objects.settings.get_value('auto-play'))
        switch_autoplay.connect('state-set', self._update_autoplay_setting)

        close_button = builder.get_object('close_btn')
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
        image = Gtk.Image.new_from_icon_name("list-add-symbolic",
                                             Gtk.IconSize.MENU)
        self._main_chooser.set_icon(image)
        self._main_chooser.set_action(self._add_chooser)
        main_chooser_box.pack_start(self._main_chooser, False, True, 0)
        if len(dirs) > 0:
            path = dirs.pop(0)
        else:
            path = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_MUSIC)
        self._main_chooser.set_dir(path)

        # Others choosers
        for directory in dirs:
            self._add_chooser(directory)

        #
        # Party mode tab
        #
        genres = Objects.genres.get()
        genres.insert(0, (-1, "Populars"))
        ids = Objects.player.get_party_ids()
        i = 0
        x = 0
        for genre_id, genre in genres:
            label = Gtk.Label()
            label.set_property('margin-start', 10)
            label.set_property('halign', Gtk.Align.START)
            label.set_text(genre)
            label.show()
            switch = Gtk.Switch()
            if genre_id in ids:
                switch.set_state(True)
            switch.connect("state-set", self._party_switch_state, genre_id)
            switch.show()
            party_grid.attach(label, x, i, 1, 1)
            party_grid.attach(switch, x+1, i, 1, 1)
            if x == 0:
                x += 2
            else:
                i += 1
                x = 0

    """
        Show dialog
    """
    def show(self):
        self._settings_dialog.show()

#######################
# PRIVATE             #
#######################

    """
        Add a new chooser widget
        @param directory path as string
    """
    def _add_chooser(self, directory=None):
        chooser = ChooserWidget()
        image = Gtk.Image.new_from_icon_name("list-remove-symbolic",
                                             Gtk.IconSize.MENU)
        chooser.set_icon(image)
        if directory:
            chooser.set_dir(directory)
        self._chooser_box.add(chooser)

    """
        Update view setting
        @param widget as unused, state as widget state
    """
    def _update_ui_setting(self, widget, state):
        Objects.settings.set_value('dark-ui',
                                   GLib.Variant('b', state))
        if not Objects.player.is_party():
            settings = Gtk.Settings.get_default()
            settings.set_property("gtk-application-prefer-dark-theme", state)

    """
        Update scan setting
        @param widget as unused, state as widget state
    """
    def _update_scan_setting(self, widget, state):
        Objects.settings.set_value('startup-scan',
                                   GLib.Variant('b', state))

    """
        Update background mode setting
        @param widget as unused, state as widget state
    """
    def _update_background_setting(self, widget, state):
        Objects.settings.set_value('background-mode',
                                   GLib.Variant('b', state))

    """
        Update save state setting
        @param widget as unused, state as widget state
    """
    def _update_state_setting(self, widget, state):
        Objects.settings.set_value('save-state',
                                   GLib.Variant('b', state))
    """
        Update auto play setting
        @param widget as unused, state as widget state
    """
    def _update_autoplay_setting(self, widget, state):
        Objects.settings.set_value('auto-play',
                                   GLib.Variant('b', state))

    """
        Close edit party dialog
        @param unused
    """
    def _edit_settings_close(self, widget):
        paths = []
        main_path = self._main_chooser.get_dir()
        choosers = self._chooser_box.get_children()
        if main_path == GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_MUSIC)\
           and not choosers:
            paths = []
        else:
            paths.append(main_path)
            for chooser in choosers:
                path = chooser.get_dir()
                if path and path not in paths:
                    paths.append(path)

        previous = Objects.settings.get_value('music-path')
        Objects.settings.set_value('music-path', GLib.Variant('as', paths))
        self._settings_dialog.hide()
        self._settings_dialog.destroy()
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


# Widget used to let user select a collection folder
class ChooserWidget(Gtk.Grid):
    def __init__(self):
        Gtk.Grid.__init__(self)
        self._action = None
        self.set_property("orientation", Gtk.Orientation.HORIZONTAL)
        self.set_property("halign", Gtk.Align.CENTER)
        self._chooser_btn = Gtk.FileChooserButton()
        self._chooser_btn.set_action(Gtk.FileChooserAction.SELECT_FOLDER)
        self._chooser_btn.set_property("margin", 5)
        self._chooser_btn.show()
        self.add(self._chooser_btn)
        self._action_btn = Gtk.Button(None)
        self._action_btn.set_property("margin", 5)
        self._action_btn.show()
        self.add(self._action_btn)
        self._action_btn.connect("clicked", self._do_action)
        self.show()

    """
        Set current selected path for chooser
        @param directory path as string
    """
    def set_dir(self, path):
        if path:
            self._chooser_btn.set_uri("file://"+path)

    """
        Set image for action button
        @param Gtk.Image
    """
    def set_icon(self, image):
        self._action_btn.set_image(image)

    """
        Set action callback for button clicked signal
        @param func
    """
    def set_action(self, action):
        self._action = action

    """
        Return select directory path
        @return path as string
    """
    def get_dir(self):
        path = GLib.uri_unescape_string(self._chooser_btn.get_uri(), None)
        if path:
            return path[7:]
        else:
            return None

#######################
# PRIVATE             #
#######################
    """
        If action defined, execute, else, remove widget
    """
    def _do_action(self, widget):
        if self._action:
            self._action()
        else:
            self.destroy()
