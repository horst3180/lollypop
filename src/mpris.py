#!/usr/bin/python
# Copyright (c) 2014 Cedric Bellegarde <gnumdk@gmail.com>
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

from lollypop.config import *
from lollypop.player import Player
from lollypop.albumart import AlbumArt
from lollypop.database import Database
from lollypop.utils import translate_artist_name

from gettext import gettext as _

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
		Objects["player"].connect('current-changed', self._on_current_changed)
		Objects["player"].connect('playback-status-changed', self._on_playback_status_changed)

	@dbus.service.method(dbus_interface=MPRIS_IFACE)
	def Raise(self):
		self._app.do_activate()

	@dbus.service.method(dbus_interface=MPRIS_IFACE)
	def Quit(self):
		self._app.quit()

	@dbus.service.method(dbus_interface=MPRIS_PLAYER_IFACE)
	def Next(self):
		Objects["player"].next()

	@dbus.service.method(dbus_interface=MPRIS_PLAYER_IFACE)
	def Previous(self):
		Objects["player"].prev()

	@dbus.service.method(dbus_interface=MPRIS_PLAYER_IFACE)
	def Pause(self):
		Objects["player"].pause()

	@dbus.service.method(dbus_interface=MPRIS_PLAYER_IFACE)
	def PlayPause(self):
		Objects["player"].play_pause()

	@dbus.service.method(dbus_interface=MPRIS_PLAYER_IFACE)
	def Stop(self):
		Objects["player"].stop()

	@dbus.service.method(dbus_interface=MPRIS_PLAYER_IFACE)
	def Play(self):
		Objects["player"].play()

	@dbus.service.method(dbus_interface=MPRIS_PLAYER_IFACE,
						 in_signature='ox')
	def SetPosition(self, track_id, position):
		pass

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
                'DesktopEntry': 'lollypop',
                'SupportedUriSchemes': [],
                'SupportedMimeTypes': [
                    'application/ogg',
                    'audio/x-vorbis+ogg',
                    'audio/x-flac',
                    'audio/mpeg'
                ],
			}
		elif interface == self.MPRIS_PLAYER_IFACE:
			return {
                'PlaybackStatus': self._get_playback_status(),
                'LoopStatus': 'Playlist',
                'Rate': dbus.Double(1.0),
                'Shuffle': True,
                'Metadata': dbus.Dictionary(self._get_metadata(), signature='sv'),
                'Volume': 100.0,
                'Position': 0.0,
                'MinimumRate': dbus.Double(1.0),
                'MaximumRate': dbus.Double(1.0),
                'CanGoNext': Objects["player"].has_next(),
                'CanGoPrevious': Objects["player"].has_previous(),
                'CanPlay': True,
                'CanPause': True,
                'CanSeek': False,
                'CanControl': False,
			}
		else:
			raise dbus.exceptions.DBusException(
				self.MPRIS_LOLLYPOP,
				'This object does not implement the %s interface'
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
		state = Objects["player"].get_status()
		if state == Gst.State.PLAYING:
			return 'Playing'
		elif state == Gst.State.PAUSED:
			return 'Paused'
		else:
			return 'Stopped'

	def _get_metadata(self):
		track_id = Objects["player"].get_current_track_id()
		if track_id == -1:
			return {}

		infos = Objects["tracks"].get_infos(track_id)
		album_id =  infos[4]
		album = Objects["albums"].get_name(album_id)
		artist = Objects["tracks"].get_artist_name(track_id)
		artist = translate_artist_name(artist)
		performer = Objects["tracks"].get_performer_name(track_id)
		performer = translate_artist_name(performer)
		genre_id = Objects["albums"].get_genre(album_id)
		genre = Objects["genres"].get_name(genre_id)
	
		metadata = {}	
		metadata['xesam:trackNumber'] = infos[3]
		metadata['xesam:title'] = infos[0]
		metadata['xesam:album'] = album
		metadata['xesam:artist'] = artist
		metadata['xesam:albumArtist'] = performer
		metadata['mpris:length'] = infos[2]
		metadata['xesam:genre'] = genre
		metadata['mpris:artUrl'] = "file://"+Objects["art"].get_path(album_id, ART_SIZE_BIG)
		
		return metadata



	def _on_current_changed(self, player, data=None):
		self.PropertiesChanged(self.MPRIS_PLAYER_IFACE,
							   {
									'Metadata': dbus.Dictionary(self._get_metadata(),
																signature='sv'),
									'CanPlay': True,
									'CanPause': True,
								},
								[])

	def _on_playback_status_changed(self, data=None):
		self.PropertiesChanged(self.MPRIS_PLAYER_IFACE,
							   {
									'PlaybackStatus': self._get_status(),
							   },
							   [])
