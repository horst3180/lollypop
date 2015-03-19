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

from gi.repository import Gtk, GdkPixbuf, GLib, GObject, Pango

from lollypop.utils import translate_artist_name
from lollypop.define import Navigation


# A selection list is a artists or genres scrolled treeview
class SelectionList(GObject.GObject):

    __gsignals__ = {
        'item-selected': (GObject.SignalFlags.RUN_FIRST, None, (int,)),
    }

    """
        Init Selection list ui
    """
    def __init__(self):
        GObject.GObject.__init__(self)

        self._model = Gtk.ListStore(int, str, GdkPixbuf.Pixbuf)
        self._model.set_sort_column_id(0, Gtk.SortType.ASCENDING)
        self._model.set_sort_func(0, self._sort_items)
        self._values = None       # Sort disabled if None
        self._is_artists = False  # for string translation
        self._stop = False        # Stop current populate
        self._to_select = None    # Item to be selected after populate
        self._populating = False  # Are we populating?
        self._timeout = None

        self._default_pixbuf = Gtk.IconTheme.get_default().load_icon(
                                            'go-next-symbolic',
                                            16,
                                            0)
        self._device_pixbuf = Gtk.IconTheme.get_default().load_icon(
                                            'multimedia-player-symbolic',
                                            16,
                                            0)
        self._view = Gtk.TreeView(model=self._model)
        self._view.set_enable_search(True)
        self._view.set_search_column(1)
        self._view.connect('cursor-changed', self._new_item_selected)

        renderer0 = Gtk.CellRendererText()
        renderer0.set_property('ellipsize-set', True)
        renderer0.set_property('ellipsize', Pango.EllipsizeMode.END)
        column0 = Gtk.TreeViewColumn('', renderer0, text=1)
        column0.set_expand(True)

        renderer1 = Gtk.CellRendererPixbuf()
        renderer1.set_property('stock-size', 16)
        column1 = Gtk.TreeViewColumn("pixbuf1", renderer1, pixbuf=2)

        self._view.append_column(column0)
        self._view.append_column(column1)

        self._view.set_headers_visible(False)
        self._view.show()

        self.widget = Gtk.ScrolledWindow()
        self.widget.set_vexpand(True)
        self.widget.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.widget.add(self._view)

    """
        Mark list as artists list
        @param is_artists as bool
    """
    def mark_as_artists(self, is_artists):
        self._is_artists = is_artists

    """
        Return True if list is marked as artists
    """
    def is_marked_as_artists(self):
        return self._is_artists

    """
        Populate view with values
        @param [(int, str)], will be deleted
        @thread safe
    """
    def populate(self, values):
        if self._timeout:
            GLib.source_remove(self._timeout)
            self._timeout = None
        # Wait for previous populate to stop
        if self._populating:
            self._timeout = GLib.timeout_add(250, self.populate, values)
        else:
            self._populating = True
            self._stop = False
            GLib.idle_add(self._model.clear)
            GLib.idle_add(self._add_item, values)

    """
        Remove row from model
        @param object id as int
    """
    def remove(self, object_id):
        for item in self._model:
            if item[0] == object_id:
                self._model.remove(item.iter)
                break

    """
        Update view with values
        @param [(int, str)]
    """
    def update(self, values):
        for item in self._model:
            found = False
            for value in values:
                if item[1] == value[1]:
                    found = True
            # Remove not found items but not devices
            if not found and item[0] > Navigation.DEVICES:
                self._model.remove(item.iter)

        self._values = values
        for value in values:
            found = False
            for item in self._model:
                if item[1] == value[1]:
                    found = True
            if not found:
                if self._is_artists:
                    string = translate_artist_name(value[1])
                else:
                    string = value[1]
                self._model.append([value[0],
                                   string,
                                   self._get_pixbuf(value[0])])
        # Disable sort
        self._values = None

    """
        Make treeview select first default item
        @param position as int
    """
    def select_item(self, position):
        try:
            iterator = self._model.get_iter(position)
            path = self._model.get_path(iterator)
            self._view.set_cursor(path, None, False)
            self._to_select = None
        except:  # list not populated yet
            self._to_select = position

    """
        Get treeview current position
        @return position as str
    """
    def get_selected_item(self):
        (path, column) = self._view.get_cursor()
        if path:
            return path.get_indices()[0]
        else:
            return -1

    """
        Get id at current position
        @return id as int
    """
    def get_selected_id(self):
        (path, column) = self._view.get_cursor()
        if path:
            iter = self._model.get_iter(path)
            if iter:
                return self._model.get_value(iter, 0)
        return None

    """
        Return items number in list
    """
    def length(self):
        return len(self._model)

    """
        Add volume
        @param device name as str
        @param object id as int <  -1000
    """
    def add_device(self, device, object_id):
        for item in self._model:
            if item[0] >= 0:
                self._model.insert_before(item.iter,
                                          [object_id,
                                           device,
                                           self._device_pixbuf])
                return
#######################
# PRIVATE             #
#######################
    """
        Add an item to the list
        @param items as [(int,str)]
    """
    def _add_item(self, values):
        if not values or self._stop:
            self._populating = False
            self._stop = False
            self._populating = False
            if self._to_select is not None and not values:
                self.select_item(self._to_select)
            del values
            values = None
            return

        (object_id, string) = values.pop(0)
        # Translating artist@@@@the => The artist
        if self._is_artists:
            string = translate_artist_name(string)

        self._model.append([object_id,
                            string,
                            self._get_pixbuf(object_id)])
        GLib.idle_add(self._add_item, values)

    """
        Return pixbuf for id
        @param ojbect_id as id
    """
    def _get_pixbuf(self, object_id):
        icon = None
        if object_id == Navigation.POPULARS:
            icon = 'emblem-favorite-symbolic'
        elif object_id == Navigation.PLAYLISTS:
            icon = 'emblem-documents-symbolic'
        elif object_id == Navigation.ALL:
            icon = 'avatar-default-symbolic'
        elif object_id == Navigation.COMPILATIONS:
            icon = 'system-users-symbolic'

        if icon:
            return Gtk.IconTheme.get_default().load_icon(
                                            icon,
                                            16,
                                            0)
        else:
            return self._default_pixbuf

    """
        Sort model
    """
    def _sort_items(self, model, itera, iterb, data):

        a = model.get_value(itera, 0)
        b = model.get_value(iterb, 0)

        if not self._values:
            return False

        # Do not order static entries
        if a < 0:
            return False
        else:
            pos_a = 0
            for rowid, string in self._values:
                if rowid == a:
                    break
                pos_a += 1
            pos_b = 0
            for rowid, string in self._values:
                if rowid == b:
                    break
                pos_b += 1

            return pos_a > pos_b

    """
        Forward "cursor-changed" as "item-selected" with item id as arg
        @param view as Gtk.TreeView
    """
    def _new_item_selected(self, view):
        if not self._populating:
            self.emit('item-selected', self.get_selected_id())
