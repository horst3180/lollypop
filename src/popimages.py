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

from gettext import gettext as _
from gi.repository import Gtk, GLib, Gio, GdkPixbuf
import urllib.request
import urllib.parse
from _thread import start_new_thread

from lollypop.define import Objects
from lollypop.define import ArtSize


# Show a popover with album covers from the web
class PopImages(Gtk.Popover):
    """
        Init Popover ui with a text entry and a scrolled treeview
        @param album id as int
    """
    def __init__(self, album_id):
        Gtk.Popover.__init__(self)

        self._album_id = album_id
        self._searched = ""

        self._view = Gtk.FlowBox()
        self._view.set_selection_mode(Gtk.SelectionMode.NONE)
        self._view.connect("child-activated", self._on_activate)
        self._view.show()

        viewport = Gtk.Viewport()
        viewport.add(self._view)
        viewport.set_property("valign", Gtk.Align.START)
        self._scroll = Gtk.ScrolledWindow()
        self._scroll.set_hexpand(True)
        self._scroll.set_vexpand(True)
        self._scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self._scroll.add(viewport)

        grid = Gtk.Grid()
        grid.set_orientation(Gtk.Orientation.VERTICAL)
        self._scroll.show()
        label = Gtk.Label()
        label.set_text(_("Select a cover art for this album"))
        grid.add(label)
        grid.add(self._scroll)
        grid.show_all()
        self.add(grid)

    """
        Populate view
        @param searched words as string
    """
    def populate(self, string):
        self._thread = True
        self._searched = string
        start_new_thread(self._populate, (string,))

    """
        Resize popover and set signals callback
    """
    def do_show(self):
        self.set_size_request(700, 400)
        Gtk.Popover.do_show(self)

    """
        Kill thread
    """
    def do_hide(self):
        self._thread = False
        Gtk.Popover.do_hide(self)

#######################
# PRIVATE             #
#######################
    """
        Same as populate()
    """
    def _populate(self, string):
        self._urls = Objects.art.get_google_arts(string)
        self._add_pixbufs()

    """
        Add urls to the view
    """
    def _add_pixbufs(self):
        if self._urls and len(self._urls) > 0:
            url = self._urls.pop()
            stream = None
            try:
                response = urllib.request.urlopen(url)
                stream = Gio.MemoryInputStream.new_from_data(
                                                response.read(), None)
            except:
                if self._thread:
                    self._add_pixbufs()
            if stream:
                GLib.idle_add(self._add_pixbuf, stream)
            if self._thread:
                self._add_pixbufs()

    """
        Add stream to the view
    """
    def _add_pixbuf(self, stream):
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_stream_at_scale(
                                            stream, ArtSize.MONSTER,
                                            ArtSize.MONSTER,
                                            False,
                                            None)
            image = Gtk.Image()
            image.set_from_pixbuf(pixbuf.scale_simple(ArtSize.BIG,
                                                      ArtSize.BIG,
                                                      2))
            image.show()
            self._view.add(image)
        except Exception as e:
            print(e)
            pass

    """
        Use pixbuf as cover
        Reset cache and use player object to announce cover change
    """
    def _on_activate(self, flowbox, child):
        pixbuf = child.get_child().get_pixbuf()
        if self._album_id:
            Objects.art.save_art(pixbuf, self._album_id)
            Objects.art.clean_cache(self._album_id)
            Objects.player.announce_cover_update(self._album_id)
        else:
            Objects.art.save_logo(pixbuf, self._searched)
            Objects.player.announce_cover_update(self._searched)            
        self.hide()
        self._streams = {}
