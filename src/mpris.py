#!/usr/bin/python
# Copyright (c) 2014-2015 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
# Copyright (c) 2013 Arnel A. Borja <kyoushuu@yahoo.com>
# Copyright (c) 2013 Vadim Rutkovsky <vrutkovs@redhat.com>
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

import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import Gst

from lollypop.define import Objects, ArtSize


class MPRIS(dbus.service.Object):
    MPRIS_IFACE = 'org.mpris.MediaPlayer2'
    MPRIS_PLAYER_IFACE = 'org.mpris.MediaPlayer2.Player'
    MPRIS_LOLLYPOP = 'org.mpris.MediaPlayer2.Lollypop'
    MPRIS_PATH = '/org/mpris/MediaPlayer2'

    def __init__(self, app):
        DBusGMainLoop(set_as_default=True)
        name = dbus.service.BusName(self.MPRIS_LOLLYPOP, dbus.SessionBus())
        dbus.service.Object.__init__(self, name, self.MPRIS_PATH)
        self._app = app
        self._metadata = {}
        Objects.player.connect('current-changed', self._on_current_changed)
        Objects.player.connect('seeked', self._on_seeked)
        Objects.player.connect('status-changed', self._on_status_changed)

    @dbus.service.method(dbus_interface=MPRIS_IFACE)
    def Raise(self):
        self._app.do_activate()

    @dbus.service.method(dbus_interface=MPRIS_IFACE)
    def Quit(self):
        self._app.quit()

    @dbus.service.method(dbus_interface=MPRIS_PLAYER_IFACE)
    def Next(self):
        Objects.player.next()

    @dbus.service.method(dbus_interface=MPRIS_PLAYER_IFACE)
    def Previous(self):
        Objects.player.prev()

    @dbus.service.method(dbus_interface=MPRIS_PLAYER_IFACE)
    def Pause(self):
        Objects.player.pause()

    @dbus.service.method(dbus_interface=MPRIS_PLAYER_IFACE)
    def PlayPause(self):
        Objects.player.play_pause()

    @dbus.service.method(dbus_interface=MPRIS_PLAYER_IFACE)
    def Stop(self):
        Objects.player.stop()

    @dbus.service.method(dbus_interface=MPRIS_PLAYER_IFACE)
    def Play(self):
        Objects.player.play()

    @dbus.service.method(dbus_interface=MPRIS_PLAYER_IFACE,
                         in_signature='ox')
    def SetPosition(self, track_id, position):
        Objects.player.seek(position/1000000)

    @dbus.service.method(dbus_interface=MPRIS_PLAYER_IFACE,
                         in_signature='s')
    def OpenUri(self, uri):
        pass

    @dbus.service.signal(dbus_interface=MPRIS_PLAYER_IFACE,
                         signature='x')
    def Seeked(self, position):
        pass

    @dbus.service.method(dbus_interface=dbus.PROPERTIES_IFACE,
                         in_signature='ss', out_signature='v')
    def Get(self, interface, property_name):
        return self.GetAll(interface)[property_name]

    @dbus.service.method(dbus_interface=dbus.PROPERTIES_IFACE,
                         in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface):
        if interface == self.MPRIS_IFACE:
            return {
                'CanQuit': True,
                'CanRaise': True,
                'HasTrackList': False,
                'Identity': 'Lollypop',
                'DesktopEntry': 'lollypop'
            }
        elif interface == self.MPRIS_PLAYER_IFACE:
            return {
                'PlaybackStatus': self._get_status(),
                'LoopStatus': 'Playlist',
                'Rate': dbus.Double(1.0),
                'Shuffle': True,
                'Metadata': dbus.Dictionary(self._metadata, signature='sv'),
                'Volume': 1.0,
                'Position': dbus.Int64(Objects.player.get_position_in_track()),
                'MinimumRate': dbus.Double(1.0),
                'MaximumRate': dbus.Double(1.0),
                'CanGoNext': True,
                'CanGoPrevious': True,
                'CanPlay': True,
                'CanPause': True,
                'CanSeek': True,
                'CanControl': True,
            }
        else:
            raise dbus.exceptions.DBusException(
                self.MPRIS_LOLLYPOP,
                "Lollypop doesn't handle %s interface"
                % interface)

    @dbus.service.method(dbus_interface=dbus.PROPERTIES_IFACE,
                         in_signature='ssv')
    def Set(self, interface, property_name, new_value):
        pass

    @dbus.service.signal(dbus_interface=dbus.PROPERTIES_IFACE,
                         signature='sa{sv}as')
    def PropertiesChanged(self, interface, changed_properties,
                          invalidated_properties):
        pass

#######################
# PRIVATE             #
#######################

    def _get_status(self):
        state = Objects.player.get_status()
        if state == Gst.State.PLAYING:
            return 'Playing'
        elif state == Gst.State.PAUSED:
            return 'Paused'
        else:
            return 'Stopped'

    def _update_metadata(self):
        if Objects.player.current.id is None:
            self._metadata = {}
        else:
            self._metadata['mpris:trackid'] = dbus.ObjectPath(
                                                '/org/lollypop/%s' %
                                                Objects.player.current.id)
            self._metadata['xesam:trackNumber'] = Objects.player.current.number
            self._metadata['xesam:title'] = Objects.player.current.title
            self._metadata['xesam:album'] = Objects.player.current.album
            self._metadata['xesam:artist'] = [Objects.player.current.artist]
            self._metadata['xesam:albumArtist'] = [
                                            Objects.player.current.aartist
                                                  ]
            self._metadata['mpris:length'] = dbus.Int64(
                                              Objects.player.current.duration *
                                              1000000
                                                       )
            self._metadata['xesam:genre'] = [Objects.player.current.genre]
            self._metadata['xesam:url'] = "file://"+Objects.player.current.path
            cover_path = Objects.art.get_path(Objects.player.current.album_id,
                                              ArtSize.BIG)
            if cover_path is not None:
                self._metadata['mpris:artUrl'] = "file://" + cover_path

    def _on_seeked(self, player, position):
        self.Seeked(position * 1000000)

    def _on_current_changed(self, player):
        self._update_metadata()
        properties = {
                'Metadata': dbus.Dictionary(self._metadata,
                                            signature='sv')
                     }
        self.PropertiesChanged(self.MPRIS_PLAYER_IFACE, properties, [])

    def _on_status_changed(self, data=None):
        properties = {'PlaybackStatus': self._get_status()}
        self.PropertiesChanged(self.MPRIS_PLAYER_IFACE, properties, [])
