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

from gi.repository import Gtk, GLib, Pango
import os
from shutil import copyfile, rmtree
from gettext import gettext as _
from _thread import start_new_thread

from lollypop.define import Objects
from lollypop.utils import translate_artist_name

# Dialog for synchronize mtp devices
class DeviceManagerWidget(Gtk.Bin):

    """
        Init ui with a scrolled treeview
        @param device as Device
        @param progress bar as Gtk.ProgressBar
        @param parent as Gtk.Widget
    """
    def __init__(self, device, progress, parent):
        Gtk.Bin.__init__(self)
        self._parent = parent
        self._device = device
        self._progress = progress
        self._playlists = None
        self._syncing = False
        self._in_thread = False
        self._total = 0  # Total files to sync
        self._done = 0   # Handled files on sync
        self._fraction = 0.0

        self._ui = Gtk.Builder()
        self._ui.add_from_resource(
                '/org/gnome/Lollypop/DeviceManager.ui'
                                  )

        self._syncing_btn = self._ui.get_object('sync_btn')
        self._syncing_btn.set_label(_("Synchronize %s") % device.name)
        self._memory_combo = self._ui.get_object('memory_combo')

        self._model = Gtk.ListStore(bool, str)
        self._model.set_sort_column_id(1, Gtk.SortType.ASCENDING)
        self._model.set_sort_func(1, self._sort_items)

        self._view = self._ui.get_object('view')
        self._view.set_model(self._model)

        self._ui.connect_signals(self)

        self.add(self._ui.get_object('widget'))
        
        self._infobar = self._ui.get_object('infobar')
        self._infobar_label = self._ui.get_object('infobarlabel')

        renderer0 = Gtk.CellRendererToggle()
        renderer0.set_property('activatable', True)
        renderer0.connect('toggled', self._on_playlist_toggled)
        column0 = Gtk.TreeViewColumn("toggle", renderer0, active=0)

        renderer1 = Gtk.CellRendererText()
        renderer1.set_property('ellipsize-set', True)
        renderer1.set_property('ellipsize', Pango.EllipsizeMode.END)
        renderer1.set_property('editable', True)
        column1 = Gtk.TreeViewColumn('text', renderer1, text=1)
        column1.set_expand(True)

        self._view.append_column(column0)
        self._view.append_column(column1)

    """
        Populate playlists, thread safe
    """
    def populate(self):
        files = os.listdir(self._device.path)
        GLib.idle_add(self._set_combo_text, files)
        if len(files) > 0:
            self._path = "%s/%s/Music/%s" %\
                        (self._device.path, files[0], "lollypop")
            try:
                if not os.path.exists(self._path):
                    os.mkdir(self._path)
                self._playlists = os.listdir(self._path)
            except:
                self._playlists = []
            
            # Search if we need to select item or not
            playlists = Objects.playlists.get()
        GLib.idle_add(self._append_playlists, playlists)
       
    """
        @return True if syncing
    """
    def is_syncing(self):
        return self._is_syncing

#######################
# PRIVATE             #
#######################
    """
        Sort model
    """
    def _sort_items(self, model, itera, iterb, data):
        a = model.get_value(itera, 1)
        b = model.get_value(iterb, 1)
        return a > b

    """
        Set combobox text
        @param text list as [str]
    """
    def _set_combo_text(self, text_list):
        for text in text_list:
            self._memory_combo.append_text(text)
        self._memory_combo.set_active(0)

    """
        Append a playlist
        @param playlists as [str]
        @param playlist selected as bool
    """
    def _append_playlists(self, playlists):
        if len(playlists) > 0:
            playlist = playlists.pop(0)
            selected = playlist in self._playlists
            self._model.append([selected, playlist])
            GLib.idle_add(self._append_playlists, playlists)
        else:
            self._view.grab_focus()
            self._view.get_selection().unselect_all()

    """
        Update progress bar smoothly
    """
    def _update_progress(self):
        current = self._progress.get_fraction()
        if self._syncing:
            progress = (self._fraction-current)/10000
        else:
            progress = 0.001

        if current < self._fraction:
            self._progress.set_fraction(current+progress)
            if not self._progress.is_visible():
                self._progress.show()
        if self._syncing or current < 1.0:
            GLib.idle_add(self._update_progress)
        else:
           GLib.timeout_add(1000, self._progress.hide)

    """
        Sync playlists with device as this
        @param playlists as [str]
    """
    def _sync(self, playlists):
        try:
            GLib.idle_add(self._progress.set_fraction, 0.0)
            self._in_thread = True
            sql = Objects.db.get_cursor()
            stat = os.statvfs(self._path)
            # For progress bar
            self._total = len(playlists)*3
            self._done = 0
            self._fraction = 0.0
            GLib.idle_add(self._update_progress)
            scan_total = 1
            for playlist in playlists:
                self._done += 1
                self._fraction = self._done/self._total
                scan_total += len(Objects.playlists.get_tracks(playlist))
                # Old tracks
                for root, dirs, files in os.walk(self._path):
                    if root.find(playlist) != -1:
                        for f in files:
                            scan_total += 1
            
            self._total = scan_total
            self._done = scan_total/3

            # Delete old playlists on device
            for f in os.listdir(self._path):
                if not self._syncing:
                    self._in_thread = False
                    return
                object_path = "%s/%s" % (self._path, f)
                if os.path.isfile(object_path) and f.endswith(".m3u"):
                    self._delete(object_path)
                elif os.path.isdir(object_path) and f not in playlists:
                    rmtree(object_path)
            self._done += 1
            self._fraction = self._done/self._total

            # Clean playlists paths
            for playlist in playlists:
                if not self._syncing:
                    self._in_thread = False
                    return
                self._clean_playlist_path(playlist, sql)

            # Delete empty directories
            for root, dirs, files in os.walk(self._path):
                for d in dirs:
                    if not self._syncing:
                        self._in_thread = False
                        return
                    dirpath = os.path.join(root, d)
                    if len(os.listdir(dirpath)) == 0:
                        self._rmdir(dirpath)
           
            self._copy_to_device(playlists, sql)
            self._fraction = 1.0
            if self._syncing:
                GLib.idle_add(self._on_sync_clicked, None)
            self._in_thread = False
        except Exception as e:
            print("DeviceManagerWidget::_sync(): %s" % e)

    """
        Copy file from playlist to device
        @param playlists as [str]
        @param sql cursor
    """
    def _copy_to_device(self, playlists, sql):
        for playlist in playlists:
            path = "%s/%s" % (self._path, playlist)
            self._mkdir(path)
            # Create playlist
            try:
                m3u = open("%s/%s.m3u" % (self._path, playlist), "w")
                m3u.write("#EXTM3U\n")
            except:
                m3u = None
            #available = self._stat.f_frsize * self._stat.f_bavail
            
            # Start copying
            tracks_id = Objects.playlists.get_tracks_id(playlist, sql)
            for track_id in tracks_id:
                if not self._syncing:
                    return
                artist_name = translate_artist_name(
                                  Objects.tracks.get_artist_name(track_id, sql))
                album_id = Objects.tracks.get_album_id(track_id, sql)
                album_name = Objects.albums.get_name(album_id, sql)
                track_path = Objects.tracks.get_path(track_id, sql)
                on_device_album_path = "%s/%s/%s_%s" % (self._path,
                                       playlist, artist_name, album_name)

                self._mkdir(on_device_album_path)

                # Copy album art
                art = Objects.art.get_art_path(album_id, sql)
                if art:
                    dst_art = "%s/folder.jpg" % on_device_album_path
                    if not os.path.exists(dst_art):
                       copyfile(art, dst_art)             

                track_name = os.path.basename(track_path)
                dst_path = "%s/%s" % (on_device_album_path, track_name)
                if m3u:
                    m3u.write("%s/%s_%s/%s\n" %\
                              (playlist,artist_name,
                               album_name, track_name))

                if not os.path.exists(dst_path):
                    copyfile(track_path, dst_path)
                self._done += 1
                self._fraction = self._done/self._total
            if m3u:
                m3u.close()

    """
        Delete files not available in playlist
        @param playlist as str
        @param sql cursor
    """
    def _clean_playlist_path(self, playlist, sql):
        tracks_id = Objects.playlists.get_tracks_id(playlist, sql)
        dst_tracks = []
        for track_id in tracks_id:
            if not self._syncing:
                return
            artist_name = translate_artist_name(
                                Objects.tracks.get_artist_name(track_id, sql))
            album_name = Objects.tracks.get_album_name(track_id, sql)
            track_path = Objects.tracks.get_path(track_id, sql)
            album_path = "%s/%s/%s_%s" % (self._path,
                         playlist, artist_name, album_name)
            track_name = os.path.basename(track_path)
            dst_path = "%s/%s" % (album_path, track_name)
            dst_tracks.append(dst_path)
        # Delete file on device and not in playlists
        for root, dirs, files in os.walk("%s/%s" % (self._path, playlist)):
            for f in files:
                if not self._syncing:
                    return
                if f != "folder.jpg":
                    filepath = os.path.join(root, f)
                    if not filepath in dst_tracks:
                        self._delete(filepath)
                self._done += 1
                self._fraction = self._done/self._total

    """
        Delete file
        @param path as str
    """
    def _delete(self, path):
        try:
            os.remove(path)
        except Exception as e:
            print("DeviceManagerWidget::_delete(): %s" % e)
        
    """
        Make dir in device
        @param path as str
    """
    def _mkdir(self, path):
        try:
            if not os.path.exists(path):
                os.mkdir(path)
        except Exception as e:
            print("DeviceManagerWidget::_mkdir(): %s" % e)

    """
        Remove dir in device
        @param path as str
    """
    def _rmdir(self, path):
        try:
            if os.path.exists(path):
                os.rmdir(path)
        except Exception as e:
            print("DeviceManagerWidget::_rmdir(): %s" % e)

    """
        Start synchronisation
        @param widget as Gtk.Button
    """
    def _on_sync_clicked(self, widget):
        if self._syncing:
            self._syncing = False
            self._memory_combo.show()
            self._view.set_sensitive(True)
            self._syncing_btn.set_label(_("Synchronize %s") % self._device.name)
        elif not self._in_thread:
            self._syncing = True
            self._memory_combo.hide()
            self._view.set_sensitive(False)
            self._syncing_btn.set_label(_("Cancel synchronization"))
            playlists = []
            for item in self._model:
                if item[0]:
                    playlists.append(item[1])
            start_new_thread(self._sync, (playlists,))

    """
        Update path
        @param combo as Gtk.ComboxText
    """
    def _on_memory_combo_changed(self, combo):
        text = combo.get_active_text()
        self._path = "%s/%s/Music/%s" % (self._device.path, text, "lollypop")
        music_path = "%s/%s/Music" % (self._device.path, text)
        try:
            if not os.path.exists(music_path):
                os.mkdir(music_path)
            if not os.path.exists(self._path):
                os.mkdir(self._path)
            self._playlists = os.listdir(self._path)
        except Exception as e:
            print("DeviceManagerWidget::_on_memory_combo_changed: %s" % e)
            self._playlists = []
        for item in self._model:
            item[0] = item[1] in self._playlists

    """
        When playlist is activated, add object to playlist
        @param widget as cell renderer
        @param path as str representation of Gtk.TreePath
    """
    def _on_playlist_toggled(self, view, path):
        iterator = self._model.get_iter(path)
        toggle = not self._model.get_value(iterator, 0)
        name = self._model.get_value(iterator, 1)
        self._model.set_value(iterator, 0, toggle)

