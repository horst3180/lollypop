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

from _thread import start_new_thread
from gettext import gettext as _
import os

from lollypop.define import Objects, Navigation
from lollypop.selectionlist import SelectionList
from lollypop.playlists import PlaylistsManager
from lollypop.view import AlbumView, ArtistView, PlaylistEditView
from lollypop.view import ViewContainer, PlaylistView, PlaylistManageView
from lollypop.view import RadiosView, DeviceView
from lollypop.collectionscanner import CollectionScanner


# This is a multimedia device
class Device:
    id = None
    name = None
    path = None
    view = None


# Container for main window child
class Container:
    def __init__(self):
        
        # Index will start at -VOLUMES
        self._devices = {}
        self._devices_index = Navigation.DEVICES
        self._show_genres = Objects.settings.get_value('show-genres')
        self._stack = ViewContainer(500)
        self._stack.show()

        self._setup_view()
        self._setup_scanner()

        self._list_one_restore = Navigation.POPULARS
        self._list_two_restore = None
        if Objects.settings.get_value('save-state'):
            self._restore_view_state()

        # Volume manager
        self._vm = Gio.VolumeMonitor.get()
        self._vm.connect('mount-added', self._on_mount_added)
        self._vm.connect('mount-removed', self._on_mount_removed)

        Objects.playlists.connect("playlists-changed",
                                  self.update_lists)

    """
        Update db at startup only if needed
        @param force as bool to force update (if possible)
    """
    def update_db(self, force=False):
        if not self._progress.is_visible():
            if force or Objects.tracks.is_empty():
                self._scanner.update(False)
            elif Objects.settings.get_value('startup-scan') or\
                 Objects.settings.get_value('force-scan'):
                self._scanner.update(True)

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
        Show playlist manager for object_id
        Current view stay present in ViewContainer
        @param object id as int
        @param genre id as int
        @param is_album as bool
    """
    def show_playlist_manager(self, object_id, genre_id, is_album):
        old_view = self._stack.get_visible_child()
        view = PlaylistManageView(object_id, genre_id, is_album,
                                  self._stack.get_allocated_width()/2)
        view.show()
        self._stack.add(view)
        self._stack.set_visible_child(view)
        start_new_thread(view.populate, ())
        # Keep previous view, 
        if isinstance(old_view, PlaylistManageView):
            old_view.destroy()

    """
        Show playlist editor for playlist
        Current view stay present in ViewContainer
        @param playlist name as str
    """
    def show_playlist_editor(self, playlist_name):
        old_view = self._stack.get_visible_child()
        view = PlaylistEditView(playlist_name,
                                self._stack.get_allocated_width()/2)
        view.show()
        self._stack.add(view)
        self._stack.set_visible_child(view)
        start_new_thread(view.populate, ())
        # Keep previous view, 
        if isinstance(old_view, PlaylistEditView):
            old_view.destroy() 

    """
        Update lists
        @param updater as GObject
    """
    def update_lists(self, updater=None):
        self._update_list_one(updater)
        self._update_list_two(updater)

    """
        Load external files
        @param files as [Gio.Files]
    """
    def load_external(self, files):
        # We wait as selection list is threaded,
        # we don't want to insert item before populated
        if self._list_one_restore is None:
            start_new_thread(self._scanner.add, (files,))
        else:
            GLib.timeout_add(250, self.load_external, files)

    """
        Get main widget
        @return Gtk.HPaned
    """
    def main_widget(self):
        return self._paned_main_list

    """
        Stop current view from processing
    """
    def stop_all(self):
        view = self._stack.get_visible_child()
        if view is not None:
            self._stack.clean_old_views(None)

    """
        Show/Hide genres
        @param bool
    """
    def show_genres(self, show):
        self._show_genres = show
        self._update_list_one(None)

    """
        Destroy current view
    """
    def destroy_current_view(self):
        view = self._stack.get_visible_child()
        view.hide()
        GLib.timeout_add(2000, view.destroy)

    """
        Update current view
    """
    def update_view(self):
        view = self._stack.get_visible_child()
        start_new_thread(view.update_covers, ())

############
# Private  #
############
    """
        Setup window main view:
            - genre list
            - artist list
            - main view as artist view or album view
    """
    def _setup_view(self):
        self._paned_main_list = Gtk.Paned.new(Gtk.Orientation.HORIZONTAL)
        self._paned_list_view = Gtk.Paned.new(Gtk.Orientation.HORIZONTAL)
        vgrid = Gtk.Grid()
        vgrid.set_orientation(Gtk.Orientation.VERTICAL)

        self._list_one = SelectionList()
        self._list_one.widget.show()
        self._list_two = SelectionList()
        self._list_one.connect('item-selected', self._on_list_one_selected)
        self._list_one.connect('populated', self._on_list_one_populated)
        self._list_two.connect('item-selected', self._on_list_two_selected)
        self._list_two.connect('populated', self._on_list_two_populated)

        self._progress = Gtk.ProgressBar()

        vgrid.add(self._stack)
        vgrid.add(self._progress)
        vgrid.show()

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
        Restore saved view
    """
    def _restore_view_state(self):
        position = Objects.settings.get_value('list-one').get_int32()
        if position != -1:
            self._list_one_restore = position
        else:
            self._list_one_restore = Navigation.POPULARS
        position = Objects.settings.get_value('list-two').get_int32()
        if position != -1:
            self._list_two_restore = position

    """
        Add genre to genre list
        @param scanner as CollectionScanner
        @param genre id as int
    """
    def _add_genre(self, scanner, genre_id):
        if self._show_genres:
            genre_name = Objects.genres.get_name(genre_id)
            self._list_one.add((genre_id, genre_name))

    """
        Add artist to artist list
        @param scanner as CollectionScanner
        @param artist id as int
        @param album id as int
    """
    def _add_artist(self, scanner, artist_id, album_id):
        artist_name = Objects.artists.get_name(artist_id)
        if self._show_genres:
            genre_ids = Objects.albums.get_genre_ids(album_id)
            if self._list_one.get_selected_id() in genre_ids:
                self._list_two.add((artist_id, artist_name))
        else:
            self._list_one.add((artist_id, artist_name))

    """
        Run collection update if needed
        @return True if hard scan is running
    """
    def _setup_scanner(self):
        self._scanner = CollectionScanner(self._progress)
        self._scanner.connect("scan-finished", self._on_scan_finished)
        self._scanner.connect("genre-update", self._add_genre)
        self._scanner.connect("artist-update", self._add_artist)
        self._scanner.connect("add-finished", self._play_tracks)

    """
        Update list one
        @param updater as GObject
    """
    def _update_list_one(self, updater):
        update = updater is not None
        # Do not update if updater is PlaylistsManager
        if not isinstance(updater, PlaylistsManager):
            if self._show_genres:
                start_new_thread(self._setup_list_genres,
                                 (self._list_one, update))
            else:
                start_new_thread(self._setup_list_artists,
                                 (self._list_one, Navigation.ALL, update))

    """
        Update list two
        @param updater as GObject
    """
    def _update_list_two(self, updater):
        if self._show_genres:
            object_id = self._list_one.get_selected_id()
            if object_id == Navigation.PLAYLISTS:
                start_new_thread(self._setup_list_playlists, (True,))
            elif isinstance(updater, CollectionScanner):
                start_new_thread(self._setup_list_artists,
                                 (self._list_two, object_id, True))

    """
        Return list one headers
    """
    def _get_headers(self):
        items = []
        items.append((Navigation.POPULARS, _("Popular albums")))
        items.append((Navigation.PLAYLISTS, _("Playlists")))
        items.append((Navigation.RADIOS, _("Radios")))
        if self._show_genres:
            items.append((Navigation.ALL, _("All artists")))
        else:
            items.append((Navigation.ALL, _("All albums")))
        return items

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
        if selection_list == self._list_one:
            if self._list_two.widget.is_visible():
                self._list_two.widget.hide()
            self._list_two_restore = None

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
            GLib.idle_add(self._update_view_playlists, None)

    """
        Update current view with device view,
        Use existing view if available
        @param object id as int
    """
    def _update_view_device(self, object_id):
        device = self._devices[object_id]

        if device and device.view:
            view = device.view
        else:
            view = DeviceView(device, self._progress,
                              self._stack.get_allocated_width()/2)
            device.view = view
            view.show()
            start_new_thread(view.populate, ())
        self._stack.add(view)
        self._stack.set_visible_child(view)
        self._stack.clean_old_views(view)

    """
        Update current view with artists view
        @param object id as int
        @param genre id as int
    """
    def _update_view_artists(self, object_id, genre_id):
        view = ArtistView(object_id, True)
        self._stack.add(view)
        view.show()
        start_new_thread(view.populate, (genre_id,))
        self._stack.set_visible_child(view)
        self._stack.clean_old_views(view)

    """
        Update current view with albums view
        @param object id as int
        @param genre id as int
    """
    def _update_view_albums(self, object_id, genre_id):
        view = AlbumView(object_id)
        self._stack.add(view)
        view.show()
        start_new_thread(view.populate, (genre_id,))
        self._stack.set_visible_child(view)
        self._stack.clean_old_views(view)

    """
        Update current view with radios view
    """
    def _update_view_radios(self):
        view = RadiosView()
        self._stack.add(view)
        view.show()
        start_new_thread(view.populate, ())
        self._stack.set_visible_child(view)
        self._stack.clean_old_views(view)

    """
        Update current view with playlist view
        @param playlist id as int
    """
    def _update_view_playlists(self, playlist_id):
        view = None
        if playlist_id is not None:
            for (p_id, p_str) in Objects.playlists.get():
                if p_id == playlist_id:
                    view = PlaylistView(p_str, self._stack)
                    break
        else:
            view = PlaylistManageView(-1, None, False,
                                      self._stack.get_allocated_width()/2)
        if view:
            view.show()
            self._stack.add(view)
            self._stack.set_visible_child(view)
            start_new_thread(view.populate, ())
            self._stack.clean_old_views(view)

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
        elif object_id < Navigation.DEVICES:
            self._list_two.widget.hide()
            self._update_view_device(object_id)
        elif object_id == Navigation.POPULARS:
            self._list_two.widget.hide()
            self._update_view_albums(object_id, None)
        elif object_id == Navigation.RADIOS:
            self._list_two.widget.hide()
            self._update_view_radios()
        elif selection_list.is_marked_as_artists():
            self._list_two.widget.hide()
            if object_id == Navigation.ALL or\
               object_id == Navigation.COMPILATIONS:
                self._update_view_albums(object_id, None)
            else:
                self._update_view_artists(object_id, None)
        else:
            start_new_thread(self._setup_list_artists,
                             (self._list_two, object_id, False))
            self._list_two.widget.show()
            if self._list_two_restore is None:
                self._update_view_albums(object_id, None)

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
        elif object_id == Navigation.COMPILATIONS:
            self._update_view_albums(object_id, selected_id)
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
        Play tracks as user playlist
        @param scanner as collection scanner
        @param outdb as bool (tracks not present in db)
    """
    def _play_tracks(self, scanner, outdb):
        ids = scanner.get_added()
        if ids:
            if not Objects.player.is_party():
                Objects.player.set_user_playlist(ids, ids[0])
            if outdb:
                Objects.settings.set_value('force-scan',
                                           GLib.Variant('b', True))
            Objects.player.load(ids[0])

    """
        Mark force scan as False, update lists
        @param scanner as CollectionScanner
    """
    def _on_scan_finished(self, scanner):
        Objects.settings.set_value('force-scan',
                                   GLib.Variant('b', False))
        self.update_lists(scanner)

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
