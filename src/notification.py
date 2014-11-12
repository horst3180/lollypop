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
# Many code inspiration from gnome-music at the GNOME project

from gi.repository import GLib, Gtk, Notify
from gettext import gettext as _

from lollypop.config import *
from lollypop.albumart import AlbumArt
from lollypop.utils import translate_artist_name

class NotificationManager:

	"""
		Init notification object with lollypop infos
	"""
	def __init__(self):

		caps = Notify.get_server_caps()
		
		self._notification = Notify.Notification()
		self._notification.set_category('x-gnome.music')
		if "action-icons" in caps:
			self._notification.set_hint('action-icons', GLib.Variant('b', True))
		if "persistence" in caps:
			self._notification.set_hint('resident', GLib.Variant('b', True))
		self._notification.set_hint('desktop-entry', GLib.Variant('s', 'lollypop'))
		if "actions" in caps:
			self._notification.add_action('media-skip-backward', _("Previous"),
									     self._go_previous, None)
			self._notification.add_action('media-skip-forward', _("Next"),
									     self._go_next, None)
		Objects["player"].connect('current-changed', self._update_track)

#######################
# PRIVATE             #
#######################

	"""
		Update notification with track_id infos
		@param player Player, track id as int
	"""
	def _update_track(self, obj, track_id):
		album_id = Objects["tracks"].get_album_id(track_id)
		album = Objects["albums"].get_name(album_id)
		artist = Objects["tracks"].get_artist_name(track_id)
		artist = translate_artist_name(artist)
		title = Objects["tracks"].get_name(track_id)
		
		self._notification.set_hint('image-path', GLib.Variant('s', Objects["art"].get_path(album_id, ART_SIZE_BIG)))
		self._notification.update(title,
								  # TRANSLATORS: by refers to the artist, from to the album
								  _("by %s, from %s") % ('<b>' + artist + '</b>',
														 '<i>' + album + '</i>'),
								  'lollypop')
		try:
			self._notification.show()
		except:
			pass

   
	"""
		Callback for notification prev button
	"""
	def _go_previous(self, notification, action, data):
		Objects["player"].prev()

	"""
		Callback for notification next button
	"""
	def _go_next(self, notification, action, data):
		Objects["player"].next()
