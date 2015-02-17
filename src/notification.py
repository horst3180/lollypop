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

from gi.repository import GLib, Notify
from gettext import gettext as _

from lollypop.define import Objects, ART_SIZE_BIG


class NotificationManager:

    """
        Init notification object with lollypop infos
    """
    def __init__(self):

        caps = Notify.get_server_caps()

        self._notification = Notify.Notification()
        self._notification.set_category('x-gnome.music')
        if "action-icons" in caps:
            self._notification.set_hint('action-icons',
                                        GLib.Variant('b', True))
        if "persistence" in caps:
            self._notification.set_hint('resident',
                                        GLib.Variant('b', True))
        self._notification.set_hint('desktop-entry',
                                    GLib.Variant('s', 'lollypop'))
        if "actions" in caps:
            self._notification.add_action('media-skip-backward',
                                          _("Previous"),
                                          self._go_previous,
                                          None)
            self._notification.add_action('media-skip-forward',
                                          _("Next"),
                                          self._go_next,
                                          None)
        Objects.player.connect('current-changed',
                               self._on_current_changed)

#######################
# PRIVATE             #
#######################

    """
        Update notification with track_id infos
        @param player Player
    """
    def _on_current_changed(self, player):
        cover_path =  Objects.art.get_path(player.current.album_id,
                                           ART_SIZE_BIG)
        if cover_path is not None:
            self._notification.set_hint('image-path',
                                        GLib.Variant('s', cover_path))
        else:
            self._notification.set_hint('image-path',
                                        GLib.Variant('s', ''))

        self._notification.update(player.current.title,
                                  # TRANSLATORS: by refers to the artist,
                                  # from to the album
                                  _("by %s, from %s") %
                                  ('<b>' + player.current.artist + '</b>',
                                   '<i>' + player.current.album + '</i>'),
                                  'lollypop')
        try:
            self._notification.show()
        except:
            pass

    """
        Callback for notification prev button
    """
    def _go_previous(self, notification, action, data):
        Objects.player.prev()

    """
        Callback for notification next button
    """
    def _go_next(self, notification, action, data):
        Objects.player.next()
