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

from gi.repository import Gtk, GdkPixbuf, GObject, Pango

from lollypop.utils import translate_artist_name
from lollypop.define import POPULARS, COMPILATIONS, ALL, PLAYLISTS


# A selection list is a artists or genres scrolled treeview
class SelectionList(GObject.GObject):

    __gsignals__ = {
        'item-selected': (GObject.SIGNAL_RUN_FIRST, None, (int,)),
    }

    """
        Init Selection list ui
    """
    def __init__(self):
        GObject.GObject.__init__(self)

        self._model = Gtk.ListStore(int, str, GdkPixbuf.Pixbuf)
        self._model.set_sort_column_id(0, Gtk.SortType.ASCENDING)
        self._model.set_sort_func(0, self._sort_items)
        self._sort = False
        self._values = None
        self._is_artists = False

        self._view = Gtk.TreeView(self._model)
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
        @param [(int, str)]
    """
    def populate(self, values):
        for (object_id, string) in values:
            # Translating artist@@@@the => The artist
            if self._is_artists:
                string = translate_artist_name(string)
            self._model.append([object_id,
                                string,
                                self._get_pixbuf(object_id)])

    """
        Clear the list
    """
    def clear(self):
        self._model.clear()

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
            if not found:
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
        @param position as str
    """
    def select_item(self, position):
        try:
            iterator = self._model.get_iter(str(position))
            path = self._model.get_path(iterator)
            self._view.set_cursor(path, None, False)
        except Exception as e:
            print("SelectionList::select_item: ", e)

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

#######################
# PRIVATE             #
#######################
    """
        Return pixbuf for id
        @param ojbect_id as id
    """
    def _get_pixbuf(self, object_id):
        icon = None
        if object_id == POPULARS:
            icon = 'emblem-favorite-symbolic'
        elif object_id == PLAYLISTS:
            icon = 'emblem-documents-symbolic'
        elif object_id == ALL:
            icon = 'avatar-default-symbolic'
        elif object_id == COMPILATIONS:
            icon = 'system-users-symbolic'
        else:
            icon = 'go-next-symbolic'
       
        return Gtk.IconTheme.get_default().load_icon(
                                            icon,
                                            16,
                                            0)

    """
        Sort model
    """
    def _sort_items(self, model, itera, iterb, data):

        a = model.get_value(itera, 0)
        b = model.get_value(iterb, 0)

        if not self._values:
            return False

        if a == POPULARS:
            return False
        elif a == ALL:
            if b == POPULARS:
                return True
            else:
                return False
        elif a == COMPILATIONS:
            if b == POPULARS or b == ALL:
                return True
            else:
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
        self._selected_id = self.get_selected_id()
        if self._selected_id is not None:
            self.emit('item-selected', self._selected_id)
