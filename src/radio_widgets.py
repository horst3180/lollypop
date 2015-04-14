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

from gi.repository import Gtk, GLib, Gdk
from cgi import escape
from gettext import gettext as _

from lollypop.define import Objects, ArtSize
from lollypop.popimages import PopImages
from lollypop.utils import translate_artist_name


# Base class for album widgets
class RadioWidget(Gtk.Bin):
    """
        Init radio widget
        @param name as str
    """
    def __init__(self, name):
        Gtk.Bin.__init__(self)
        self._name = name
        self._selected = None
        self._cover = None
        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/RadioWidget.ui')
        builder.connect_signals(self)
        self._cover = builder.get_object('cover')
        
    """
        Set cover for album if state changed
        @param force as bool
    """
    def set_cover(self, force=False):
        selected = self._name==Objects.player.current.title
        if self._cover and (selected != self._selected or force):
            self._selected = selected
            self._cover.set_from_pixbuf(
                    Objects.art.get_radio(
                                self._name,
                                ArtSize.BIG,
                                selected))

    """
        Update cover for album id id needed
        @param name as str
    """
    def update_cover(self, name):
        if self._cover and self._name == name:
            self._selected = self._name==Objects.player.current.title
            self._cover.set_from_pixbuf(Objects.art.get_radio(name,
                                                              ArtSize.BIG,
                                                              self._selected))
    """
        Update playing indicator
    """
    def update_playing_indicator(self):
        pass

    """
        Stop populating
    """
    def stop(self):
        self._stop = True

#######################
# PRIVATE             #
#######################
    """
        Play this radio
        @param widget as Gtk.Widget
    """
    def _on_play_clicked(self, widget):
        pass

    """
        Edit this radio
        @param widget as Gtk.Widget
    """
    def _on_edit_clicked(self, widget):
        pass

    """
        Remove this radio
        @param widget as Gtk.Widget
    """
    def _on_remove_clicked(self, widget):
        pass

    """
        Add hover style
        @param widget as Gtk.Widget
        @param event es Gdk.Event
    """
    def _on_enter_notify(self, widget, event):
        self.get_style_context().add_class('hovereffect')

    """
        Remove hover style
        @param widget as Gtk.Widget
        @param event es Gdk.Event
    """
    def _on_leave_notify(self, widget, event):
        self.get_style_context().remove_class('hovereffect')
