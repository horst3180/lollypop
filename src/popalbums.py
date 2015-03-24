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
from _thread import start_new_thread

from lollypop.container import ViewContainer
from lollypop.view import ArtistView
from lollypop.define import Objects


# Show a popup with current artist albums
class PopAlbums(Gtk.Popover, ViewContainer):

    """
        Init Popover ui with a text entry and a scrolled treeview
    """
    def __init__(self):
        Gtk.Popover.__init__(self)
        ViewContainer.__init__(self, 1000)

        self._on_screen_artist = None
        self.add(self._stack)

        Objects.player.connect("current-changed", self._update_content)

    """
        Run _populate in a thread
    """
    def populate(self):
        if self._on_screen_artist != Objects.player.current.performer_id:
            self._on_screen_artist = Objects.player.current.performer_id
            previous = self._stack.get_visible_child()
            view = ArtistView(self._on_screen_artist, False)
            view.show()
            start_new_thread(view.populate, (None,))
            self._stack.add(view)
            self._stack.set_visible_child(view)
            self._clean_view(previous)

    """
        Resize popover
    """
    def do_show(self):
        size_setting = Objects.settings.get_value('window-size')
        if isinstance(size_setting[0], int) and\
           isinstance(size_setting[1], int):
            self.set_size_request(size_setting[0]*0.65, size_setting[1]*0.8)
        else:
            self.set_size_request(600, 600)
        Gtk.Popover.do_show(self)

    """
        Remove view
    """
    def do_hide(self):
        Gtk.Popover.do_hide(self)
        child = self._stack.get_visible_child()
        child.stop()
        self._on_screen_artist = None
        GLib.timeout_add(1000, self._clean_view, child)

#######################
# PRIVATE             #
#######################
    """
        Update the content view
        @param player as Player
        @param track id as int
    """
    def _update_content(self, player):
        if self.is_visible():
            self.populate()
