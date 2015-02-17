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

from gi.repository import GObject, Gtk

from lollypop.define import Objects, ART_SIZE_MEDIUM
from lollypop.popmenu import PopMainMenu
from lollypop.utils import seconds_to_string


# A track row with track informations
class TrackRow(Gtk.ListBoxRow):
    """
        Init row widgets
    """
    def __init__(self):
        Gtk.ListBoxRow.__init__(self)
        self._object_id = None
        self._num = 0
        self._number = 0
        self._ui = Gtk.Builder()
        self._ui.add_from_resource('/org/gnome/Lollypop/TrackRow.ui')
        self._row_widget = self._ui.get_object('row')
        self._ui.get_object('menu').connect('clicked', self._pop_menu)
        self.add(self._row_widget)
        self.get_style_context().add_class('trackrow')
        self.show()

    """
        Destroy all widgets
    """
    def destroy(self):
        self.remove(self._row_widget)
        for widget in self._ui.get_objects():
            widget.destroy()
        Gtk.ListBoxRow.destroy(self)

    """
        Show play icon
        @param widget name as str
        @param show as bool
    """
    def show_widget(self, name, show):
        widget = self._ui.get_object(name)
        if name == "icon":
            if show:
                widget.set_from_icon_name('media-playback-start-symbolic', 1)
                self.get_style_context().remove_class('trackrow')
                self.get_style_context().add_class('trackrowplaying')
            else:
                widget.clear()
                self.get_style_context().remove_class('trackrowplaying')
                self.get_style_context().add_class('trackrow')
        else:
            if show:
                widget.show()
            else:
                widget.hide()

    """
        Set object label
        @param object as string
        @param label as string
    """
    def set_label(self, obj, label):
        self._ui.get_object(obj).set_markup(label)

    """
        Get object label
    """
    def get_label(self, obj):
        return self._ui.get_object(obj).get_text()

    """
        Store current object id
        @param object id as int
    """
    def set_object_id(self, object_id):
        self._object_id = object_id

    """
        Get object id
        @return Current object id as int
    """
    def get_object_id(self):
        return self._object_id

    """
        Set track number
        @param num as int
    """
    def set_number(self, num):
        self._number = num

    """
        Get track number
        @return num as int
    """
    def get_number(self):
        return self._number

    """
        Set cover
        @param cover as Gdk.Pixbuf
    """
    def set_cover(self, pixbuf):
        self._ui.get_object('cover').set_from_pixbuf(pixbuf)

#######################
# PRIVATE             #
#######################
    """
        Popup menu for track
        @param widget as Gtk.Button
    """
    def _pop_menu(self, widget):
        menu = PopMainMenu(self._object_id, False, False, widget)
        popover = Gtk.Popover.new_from_model(self._ui.get_object('menu'), menu)
        popover.connect('closed', self._on_closed)
        self.get_style_context().add_class('trackrowmenu')
        popover.show()
    """
        Remove selected style
        @param widget as Gtk.Popover
    """
    def _on_closed(self, widget):
        self.get_style_context().remove_class('trackrowmenu')

######################################################################
######################################################################


# Track list of track rows
class TracksWidget(Gtk.ListBox):

    __gsignals__ = {
        'activated': (GObject.SIGNAL_RUN_FIRST, None, (int,))
    }

    """
        Init track widget
        @param show_menu as bool if menu need to be displayed
    """
    def __init__(self, show_menu):
        Gtk.ListBox.__init__(self)
        self._show_menu = show_menu
        self.connect("row-activated", self._on_activate)
        self.get_style_context().add_class('trackswidget')

    """
        Add track to list
        @param track id as int
        @param track number as int
        @param title as str
        @param length as str
        @param pos as int
        @param show cover as bool
    """
    def add_track(self, track_id, num, title, length,
                  pos, show_cover=False):
        track_row = TrackRow()
        track_row.show_widget('cover', show_cover)
        track_row.show_widget('menu', self._show_menu)
        if Objects.player.current.id == track_id:
            track_row.show_widget('icon', True)
        if pos:
            track_row.set_label('num',
                                '''<span foreground="#72729f9fcfcf"\
                                font_desc="Bold">%s</span>''' % str(pos))
        else:
            track_row.set_label('num', str(num))
        track_row.set_number(num)
        track_row.set_label('title', title)
        track_row.set_label('duration', seconds_to_string(length))
        track_row.set_object_id(track_id)
        if show_cover:
            album_id = Objects.tracks.get_album_id(track_id)
            track_row.set_cover(Objects.art.get(album_id, ART_SIZE_MEDIUM))
        track_row.show()
        self.add(track_row)

    """
        Update playing track
        @param track id as int
    """
    def update_playing(self, track_id):
        for row in self.get_children():
            if row.get_object_id() == track_id:
                row.show_widget('icon', True)
            else:
                row.show_widget('icon', False)

    """
        Set signals callback
    """
    def do_show(self):
        Objects.player.connect("queue-changed", self._update_pos_label)
        Gtk.ListBox.do_show(self)

    """
        Clean signals callback
    """
    def do_hide(self):
        Objects.player.disconnect_by_func(self._update_pos_label)
        Gtk.ListBox.do_hide(self)

#######################
# PRIVATE             #
#######################
    """
        Update position label
        @param player
        @param track id as int
    """
    def _update_pos_label(self, widget):
        for row in self.get_children():
            track_id = row.get_object_id()
            if Objects.player.is_in_queue(track_id):
                pos = Objects.player.get_track_position(track_id)
                row.set_label('num',
                              '''<span foreground="#72729f9fcfcf"\
                              font_desc="Bold">%s</span>''' % str(pos))
            else:
                row.set_label('num', str(row.get_number()))

    """
        Play activated item
        @param widget as TracksWidget
        @param row as TrackRow
    """
    def _on_activate(self, widget, row):
        self.emit('activated', row.get_object_id())
