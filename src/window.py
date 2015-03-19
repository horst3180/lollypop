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
from gettext import gettext as _
from _thread import start_new_thread
import os

from lollypop.define import Objects, Navigation
from lollypop.collectionscanner import CollectionScanner
from lollypop.toolbar import Toolbar
from lollypop.selectionlist import SelectionList
from lollypop.playlists import PlaylistsManager
from lollypop.view import ViewContainer, AlbumView, ArtistView, DeviceView
from lollypop.view import PlaylistView, PlaylistManageView, LoadingView


# This is a multimedia device
class Device:
    def __init__(self):
        self.id = None
        self.name = None
        self.path = None
        self.view = None


# Main window
class Window(Gtk.ApplicationWindow, ViewContainer):
    """
        Init window objects
    """
    def __init__(self, app):
        Gtk.ApplicationWindow.__init__(self,
                                       application=app,
                                       title="Lollypop")
        ViewContainer.__init__(self, 500)
        self._timeout_configure = None
        # Same for volumes, as volumes are in list one,
        # Index will start at -VOLUMES
        self._devices = {}
        self._devices_index = Navigation.DEVICES

        self._setup_window()
        self._setup_view()

        if not self._setup_scanner():
            self._setup_lists(False)
            self._list_one.widget.show()

        self._list_one_restore = None
        self._list_two_restore = None
        if Objects.settings.get_value('save-state'):
            self._restore_view_state()
        else:
            self._list_one_restore = Navigation.POPULARS
            self._list_two_restore = None


        self._setup_media_keys()

        # Volume manager
        self._vm = Gio.VolumeMonitor.get()
        self._vm.connect('mount-added', self._on_mount_added)
        self._vm.connect('mount-removed', self._on_mount_removed)

        party_settings = Objects.settings.get_value('party-ids')
        ids = []
        for setting in party_settings:
            if isinstance(setting, int):
                ids.append(setting)
        Objects.player.set_party_ids(ids)
        self.connect("destroy", self._on_destroyed_window)
        Objects.playlists.connect("playlists-changed",
                                  self._update_lists)

    """
        Update music database
    """
    def update_db(self):
        if not self._progress.is_visible():
            self._list_one.widget.hide()
            self._list_one_restore = self._list_one.get_selected_id()
            self._list_two.widget.hide()
            self._list_two_restore = self._list_two.get_selected_id()
            old_view = self._stack.get_visible_child()
            view = LoadingView()
            self._stack.add(view)
            self._stack.set_visible_child(view)
            self.save_view_state()
            self._scanner.update(self._progress, False)
            self._clean_view(old_view)

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
        Objects.settings.set_value("list-one",
                                   GLib.Variant(
                                        'i',
                                        self._list_one.get_selected_id()))
        Objects.settings.set_value("list-two",
                                   GLib.Variant(
                                        'i',
                                        self._list_two.get_selected_id()))

    """
        Show playlist manager for playlist id/object_id
        @param object id as int
        @param is_album as bool
    """
    def show_playlist_manager(self, object_id, is_album):
        old_view = self._stack.get_visible_child()
        view = PlaylistManageView(object_id, is_album)
        view.show()
        self._stack.add(view)
        self._stack.set_visible_child(view)
        start_new_thread(view.populate, ())
        if isinstance(old_view, PlaylistManageView):
            old_view.destroy()

    """
        Destroy current view
    """
    def destroy_current_view(self):
        view = self._stack.get_visible_child()
        view.hide()
        GLib.timeout_add(2000, view.destroy)

############
# Private  #
############
    """
        Restore saved view
    """
    def _restore_view_state(self):
        position = Objects.settings.get_value('list-one').get_int32()
        if position != -1:
            self._list_one_restore = position
        position = Objects.settings.get_value('list-two').get_int32()
        if position != -1:
            self._list_two_restore = position


    """
        Run collection update if needed
        @return True if hard scan is running
    """
    def _setup_scanner(self):
        self._scanner = CollectionScanner()
        self._scanner.connect("scan-finished", self._update_lists)
        if not self._progress.is_visible():
            if Objects.tracks.is_empty():
                self._scanner.update(self._progress, False)
                return True
            elif Objects.settings.get_value('startup-scan'):
                self._scanner.update(self._progress, True)
                return False

    """
        Update lists after scan
        @param updater as GObject
    """
    def _update_lists(self, updater):
        if not self._list_one.widget.is_visible():
            self._list_one.widget.show()
        self._update_list_one(updater)
        if self._list_two.visible:
            self._list_two.widget.show()
            self._update_list_two(updater)
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
        if object_id == Navigation.PLAYLISTS:
            start_new_thread(self._setup_list_playlists, (True,))
        elif isinstance(updater, CollectionScanner):
            start_new_thread(self._setup_list_artists,
                             (self._list_two, object_id, True))

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

        self._toolbar = Toolbar(self.get_application())
        self._toolbar.header_bar.show()
        self._toolbar.get_view_genres_btn().connect(
                                            "toggled",
                                            self._on_genres_btn_toggled)
        self._show_genres = self._toolbar.get_view_genres_btn().get_active()

        self._list_one = SelectionList()
        self._list_two = SelectionList()
        self._list_one.connect('item-selected', self._on_list_one_selected)
        self._list_one.connect('populated', self._on_list_one_populated)
        self._list_two.connect('item-selected', self._on_list_two_selected)
        self._list_two.connect('populated', self._on_list_two_populated)
        self._list_two.visible = False

        loading_view = LoadingView()
        self._stack.add(loading_view)
        self._stack.set_visible_child(loading_view)

        self._progress = Gtk.ProgressBar()

        vgrid.add(self._stack)
        vgrid.add(self._progress)
        vgrid.show()

        # Only set headerbar on Gnome Shell and Pantheon Shell
        DESKTOP = os.environ.get("XDG_CURRENT_DESKTOP")
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
        self._paned_main_list.set_position(
                        Objects.settings.get_value(
                                "paned-mainlist-width").get_int32())
        self._paned_list_view.set_position(
                        Objects.settings.get_value(
                                "paned-listview-width").get_int32())
        self._paned_main_list.show()
        self._paned_list_view.show()

    """
        Return list one headers
    """
    def _get_headers(self):
        items = []
        items.append((Navigation.POPULARS, _("Popular albums")))
        items.append((Navigation.PLAYLISTS, _("Playlists")))
        if self._show_genres:
            items.append((Navigation.ALL, _("All artists")))
        else:
            items.append((Navigation.ALL, _("All albums")))
        return items

    """
        Setup genres/artists lists
        @param update as bool, if True, just update entries
    """
    def _setup_lists(self, update):
        if self._show_genres:
            start_new_thread(self._setup_list_genres,
                             (self._list_one, update))
        else:
            start_new_thread(self._setup_list_artists,
                             (self._list_one, Navigation.ALL, update))

    """
        Setup list for genres
        @param list as SelectionList
        @param update as bool, if True, just update entries
        @thread safe
    """
    def _setup_list_genres(self, selection_list, update):
        sql = Objects.db.get_cursor()
        selection_list.mark_as_artists(False)
        items = self._get_headers() + Objects.genres.get(sql)
        if update:
            GLib.idle_add(selection_list.update, items)
        else:
            selection_list.populate(items)
        sql.close()

    """
        Hide list two base on current artist list
    """
    def _pre_setup_list_artists(self, selection_list):
        if selection_list == self._list_one and\
           self._list_two.widget.is_visible():
            self._list_two.widget.hide()
            self._list_two.visible = False

    """
        Setup list for artists
        @param list as SelectionList
        @param update as bool, if True, just update entries
        @thread safe
    """
    def _setup_list_artists(self, selection_list, genre_id, update):
        GLib.idle_add(self._pre_setup_list_artists, selection_list)
        sql = Objects.db.get_cursor()
        items = []
        selection_list.mark_as_artists(True)
        if selection_list == self._list_one:
            items = self._get_headers()
        if len(Objects.albums.get_compilations(genre_id, sql)) > 0:
            items.append((Navigation.COMPILATIONS, _("Compilations")))

        items += Objects.artists.get(genre_id, sql)

        if update:
            GLib.idle_add(selection_list.update, items)
        else:
            selection_list.populate(items)
        sql.close()

    """
        Setup list for playlists
        @param update as bool
    """
    def _setup_list_playlists(self, update):
        playlists = Objects.playlists.get()
        if update:
            self._list_two.update(playlists)
        else:
            self._list_two.mark_as_artists(False)
            self._list_two.populate(playlists)

        # Only update view on list populate
        if not update:
            GLib.idle_add(self._update_view_playlists, None)

    """
        Update current view with device view,
        Use existing view if available
        @param object id as int
    """
    def _update_view_device(self, object_id):
        old_view = self._stack.get_visible_child()
        device = self._devices[object_id]

        # Only restore previous widget if not syncing
        if device and device.view and not device.view.is_syncing():
            device.view.destroy()
            device.view = None

        if device.view:
            view = device.view
        else:
            view = DeviceView(device, self._progress)
            device.view = view
            view.show()
            start_new_thread(view.populate, ())
            self._stack.add(view)
        self._stack.set_visible_child(view)
        self._clean_view(old_view)

    """
        Update current view with artists view
        @param object id as int
        @param genre id as int
    """
    def _update_view_artists(self, object_id, genre_id):
        old_view = self._stack.get_visible_child()
        view = ArtistView(object_id, True)
        self._stack.add(view)
        start_new_thread(view.populate, (genre_id,))
        self._stack.set_visible_child(view)
        self._clean_view(old_view)

    """
        Update current view with albums view
    """
    def _update_view_albums(self, genre_id):
        old_view = self._stack.get_visible_child()
        view = AlbumView()
        self._stack.add(view)
        start_new_thread(view.populate, (genre_id,))
        self._stack.set_visible_child(view)
        self._clean_view(old_view)

    """
        Update current view with playlist view
        @param playlist id as int
    """
    def _update_view_playlists(self, playlist_id):
        old_view = self._stack.get_visible_child()
        view = None
        if playlist_id is not None:
            for (p_id, p_str) in Objects.playlists.get():
                if p_id == playlist_id:
                    view = PlaylistView(p_str)
                    break
        else:
            view = PlaylistManageView(-1, None)
        if view:
            view.show()
            self._stack.add(view)
            self._stack.set_visible_child(view)
            start_new_thread(view.populate, ())
            self._clean_view(old_view)

    """
        Add volume to device list
        @param volume as Gio.Volume
    """
    def _add_device(self, volume):
        if volume is None:
            return
        root = volume.get_activation_root()
        if root is None:
            return
        path = root.get_path()
        if path and path.find('mtp:') != -1:
            self._devices_index -= 1
            dev = Device()
            dev.id = self._devices_index
            dev.name = volume.get_name()
            dev.path = path
            self._devices[self._devices_index] = dev
            self._list_one.add_device(dev.name, dev.id)

    """
        Remove volume from device list
        @param volume as Gio.Volume
    """
    def _remove_device(self, volume):
        for dev in self._devices.values():
            if not os.path.exists(dev.path):
                self._list_one.remove(dev.id)
                device = self._devices[dev.id]
                if device.view:
                    device.view.destroy()
                del self._devices[dev.id]
            break

    """
        Update view based on selected object
        @param list as SelectionList
        @param object id as int
    """
    def _on_list_one_selected(self, selection_list, object_id):
        if object_id == Navigation.PLAYLISTS:
            start_new_thread(self._setup_list_playlists, (False,))
            self._list_two.widget.show()
            self._list_two.visible = True
        elif object_id < Navigation.DEVICES:
            self._list_two.widget.hide()
            self._list_two.visible = False
            self._update_view_device(object_id)
        elif object_id == Navigation.POPULARS:
            self._list_two.widget.hide()
            self._list_two.visible = False
            self._update_view_albums(object_id)
        elif selection_list.is_marked_as_artists():
            self._list_two.widget.hide()
            self._list_two.visible = False
            if object_id == Navigation.ALL:
                self._update_view_albums(object_id)
            else:
                self._update_view_artists(object_id, None)
        else:
            start_new_thread(self._setup_list_artists,
                             (self._list_two, object_id, False))
            self._list_two.widget.show()
            self._list_two.visible = True
            if self._list_two_restore is None:   
                self._update_view_albums(object_id)

    """
        Restore previous state
        @param selection list as SelectionList
    """
    def _on_list_one_populated(self, selection_list):
        if self._list_one_restore is not None:
            self._list_one.select_id(self._list_one_restore)
            self._list_one_restore = None
        for dev in self._devices.values():
            self._list_one.add_device(dev.name, dev.id)


    """
        Update view based on selected object
        @param list as SelectionList
        @param object id as int
    """
    def _on_list_two_selected(self, selection_list, object_id):
        selected_id = self._list_one.get_selected_id()
        if selected_id == Navigation.PLAYLISTS:
            self._update_view_playlists(object_id)
        elif selected_id == Navigation.ALL:
            self._update_view_artists(object_id, None)
        else:
            self._update_view_artists(object_id, selected_id)

    """
        Restore previous state
        @param selection list as SelectionList
    """
    def _on_list_two_populated(self, selection_list):
        if self._list_two_restore is not None:
            self._list_two.select_id(self._list_two_restore)
            self._list_two_restore = None

    """
        On genres button toggled, update lists/views
    """
    def _on_genres_btn_toggled(self, button):
        self._show_genres = self._toolbar.get_view_genres_btn().get_active()
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

    """
        On volume mounter
        @param vm as Gio.VolumeMonitor
        @param mnt as Gio.Mount
    """
    def _on_mount_added(self, vm, mnt):
        self._add_device(mnt.get_volume())

    """
        On volume removed, clean selection list
        @param vm as Gio.VolumeMonitor
        @param mnt as Gio.Mount
    """
    def _on_mount_removed(self, vm, mnt):
        self._remove_device(mnt.get_volume())
