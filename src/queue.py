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

from gi.repository import Gtk, GLib, GdkPixbuf, Pango
from cgi import escape

from lollypop.define import Objects, ART_SIZE_MEDIUM
from lollypop.utils import translate_artist_name

######################################################################
######################################################################


# Widget to manage queue
class QueueWidget(Gtk.Popover):
    """
        Init Popover ui with a text entry and a scrolled treeview
    """
    def __init__(self):
        Gtk.Popover.__init__(self)

        self.set_property('width-request', 400)

        self._timeout = None
        self._in_drag = False
        self._del_pixbuf = Gtk.IconTheme.get_default().load_icon(
                                            "list-remove-symbolic",
                                            22,
                                            0)

        self._ui = Gtk.Builder()
        self._ui.add_from_resource(
                        '/org/gnome/Lollypop/QueueWidget.ui')

        self._model = Gtk.ListStore(GdkPixbuf.Pixbuf,
                                    str,
                                    GdkPixbuf.Pixbuf,
                                    int)
        self._model.connect("row-deleted", self._updated_rows)

        self._view = self._ui.get_object('view')
        self._view.set_model(self._model)

        self._ui.connect_signals(self)

        self._widget = self._ui.get_object('widget')

        renderer0 = Gtk.CellRendererPixbuf()
        renderer0.set_property('stock-size', ART_SIZE_MEDIUM)
        column0 = Gtk.TreeViewColumn("pixbuf1", renderer0, pixbuf=0)

        renderer1 = Gtk.CellRendererText()
        renderer1.set_property('ellipsize-set', True)
        renderer1.set_property('ellipsize', Pango.EllipsizeMode.END)
        column1 = Gtk.TreeViewColumn("text", renderer1, markup=1)
        column1.set_expand(True)

        renderer2 = Gtk.CellRendererPixbuf()
        renderer2.set_property('stock-size', 22)
        renderer2.set_fixed_size(22, -1)
        column2 = Gtk.TreeViewColumn("pixbuf2", renderer2, pixbuf=2)

        self._view.append_column(column0)
        self._view.append_column(column1)
        self._view.append_column(column2)

        self.add(self._widget)

    """
        Show queue popover
        Populate treeview with current queue
    """
    def do_show(self):
        size_setting = Objects.settings.get_value('window-size')
        if isinstance(size_setting[1], int):
            self.set_property('height-request', size_setting[1]*0.7)
        else:
            self.set_property('height-request', 600)

        for track_id in Objects.player.get_queue():
            album_id = Objects.tracks.get_album_id(track_id)
            artist_id = Objects.albums.get_artist_id(album_id)
            artist_name = Objects.artists.get_name(artist_id)
            track_name = Objects.tracks.get_name(track_id)
            art = Objects.art.get(album_id, ART_SIZE_MEDIUM)
            self._model.append([art,
                                "<b>%s</b>\n%s" %
                                (escape(translate_artist_name(artist_name)),
                                 escape(track_name)),
                                self._del_pixbuf,
                                track_id])

        Objects.player.connect("current-changed", self._on_current_changed)
        Gtk.Popover.do_show(self)

    """
        Clear model
    """
    def do_hide(self):
        Gtk.Popover.do_hide(self)
        self._model.clear()
        Objects.player.disconnect_by_func(self._on_current_changed)

#######################
# PRIVATE             #
#######################
    """
        Delete item if Delete was pressed
        @param widget unused, Gtk.Event
    """
    def _on_keyboard_event(self, widget, event):
        if len(Objects.player.get_queue()) > 0:
            if event.keyval == 65535:
                path, column = self._view.get_cursor()
                iterator = self._model.get_iter(path)
                self._model.remove(iterator)

    """
        Pop first item in queue if it's current track id
        @param player object
    """
    def _on_current_changed(self, player):
        if len(self._model) > 0:
            row = self._model[0]
            if row[3] == player.current.id:
                iter = self._model.get_iter(row.path)
                self._model.remove(iter)

    """
        Mark as in drag
        @param unused
    """
    def _on_drag_begin(self, widget, context):
        self._in_drag = True

    """
        Mark as not in drag
        @param unused
    """
    def _on_drag_end(self, widget, context):
        self._in_drag = False

    """
        Update queue when a row has been deleted
        @param path as Gtk.TreePath
        @param data as unused
    """
    def _updated_rows(self, path, data):
        if self.is_visible():
            new_queue = []
            for row in self._model:
                if row[3]:
                    new_queue.append(row[3])
            Objects.player.set_queue(new_queue)

    """
        Delete row
        @param GtkTreeIter
    """
    def _delete_row(self, iterator):
        self._model.remove(iterator)

    """
        Play clicked item
        @param TreeView, TreePath, TreeViewColumn
    """
    def _on_row_activated(self, view, path, column):
        if self._timeout:
            return
        iterator = self._model.get_iter(path)
        if iterator:
            if column.get_title() == "pixbuf2":
                self._delete_row(iterator)
            else:
                # We don't want to play if we are
                # starting a drag & drop, so delay
                self._timeout = GLib.timeout_add(500,
                                                 self._play_track,
                                                 iterator)

    """
        Clear queue
        @param widget as Gtk.Button
    """
    def _on_button_clicked(self, widget):
        self._model.clear()

    """
        Play track for selected iter
        @param GtkTreeIter
    """
    def _play_track(self, iterator):
        self._timeout = None
        if not self._in_drag:
            value_id = self._model.get_value(iterator, 3)
            self._model.remove(iterator)
            Objects.player.load(value_id)
