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
from gettext import gettext as _
from _thread import start_new_thread

from lollypop.define import Objects

# Dialog for synchronize mtp devices
class DeviceManagerWidget(Gtk.Bin):

    """
        Init ui with a scrolled treeview
        @param device as Device
        @param parent as Gtk.Widget
    """
    def __init__(self, device, parent):
        Gtk.Bin.__init__(self)
        self._parent = parent
        self._device = device
        self._playlists = None
        self._syncing = False

        self._ui = Gtk.Builder()
        self._ui.add_from_resource(
                '/org/gnome/Lollypop/DeviceManager.ui'
                                  )

        self._sync_btn = self._ui.get_object('sync_btn')
        self._sync_btn.set_label(_("Synchronize %s") % device.name)
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
        Calculate size
    """
    def calculate_size(self):
        if self._parent:
            self._ui.get_object('scroll').set_property('width-request',
                                    self._parent.get_allocated_width()/2)

    """
        Populate playlists, thread safe
    """
    def populate(self):
        files = os.listdir(self._device.path)
        GLib.idle_add(self._set_combo_text, files)
        if len(files) > 0:
            self._path = "%s/%s/Music/%s" % (self._device.path, files[0], "lollypop")
            try:
                if not os.path.exists(self._path):
                    os.mkdir(self._path)
                self._playlists = os.listdir(self._path)
            except:
                self._playlists = []
            
            # Search if we need to select item or not
            playlists = Objects.playlists.get()
        GLib.idle_add(self._append_playlists, playlists)
       
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
        Sync playlists with device as this:
        
    """
    """
        Make dir in device
        @param name as str
    """
    def _mkdir(self, name):
        try:
            os.mkdir("%s/%s" % (self._path, name))
        except Exception as e:
            print(e)


    """
        Start synchronisation
        @param widget as Gtk.Button
    """
    def _on_sync_clicked(self, widget):
        if self._syncing:
            self._syncing = False
            self._memory_combo.show()
            self._view.set_sensitive(True)
            self._sync_btn.set_label(_("Synchronize %s") % self._device.name)
        else:
            self._syncing = True
            self._memory_combo.hide()
            self._view.set_sensitive(False)
            self._sync_btn.set_label(_("Cancel synchronization"))
            #start_new_thread(self._sync, ())

    """
        Update path
        @param combo as Gtk.ComboxText
    """
    def _on_memory_combo_changed(self, combo):
        text = combo.get_active_text()
        self._path = "%s/%s/Music/%s" % (self._device.path, text, "lollypop")
        try:
            if not os.path.exists(self._path):
                os.mkdir(self._path)
            self._playlists = os.listdir(self._path)
        except:
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

