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

import os, time
import sqlite3
from gettext import gettext as _, ngettext    
from gi.repository import GLib, Gdk, GObject
import mutagen
from lollypop.database import Database
from lollypop.utils import format_artist_name

class CollectionScanner(GObject.GObject):
	__gsignals__ = {
		'scan-finished': (GObject.SIGNAL_RUN_FIRST, None, ()),
	}
	_mimes = [ "mp3", "ogg", "flac", "m4a", "mp4" ]
	def __init__(self, db, paths):
		GObject.GObject.__init__(self)
		self._db = db
		if len(paths) > 0:
			self._paths = paths
		else:
			self._paths = [ GLib.get_user_special_dir(GLib.USER_DIRECTORY_MUSIC) ]

	"""
		Update database if empty
	"""
	def update(self):
		GLib.idle_add(self._scan)

#######################
# PRIVATE             #
#######################

	"""
		Scan music collection for music files
	"""
	def _scan(self):
		tracks = self._db.get_tracks_filepath()
		for path in self._paths:
			for root, dirs, files in os.walk(path):
				for f in files:
					lowername = f.lower()
					supported = False
					for mime in self._mimes:
						if lowername.endswith(mime):
							supported = True
							break	
					if (supported):
						filepath = os.path.join(root, f)
						try:
							if filepath not in tracks:
								tag = mutagen.File(filepath, easy = True)
								self._add2db(filepath, tag)
							else:
								tracks.remove(filepath)
						
						except Exception as e:
							print("CollectionScanner::_scan(): %s" %e)

		# Clean deleted files
		for track in tracks:
			self._db.remove_track(track)

		self._db.commit()
		self._db.clean()
		self._db.compilation_lookup()
		self.emit("scan-finished")

	"""
		Add new file to db with tag
	"""
	def _add2db(self, filepath, tag):
		path = os.path.dirname(filepath)

		keys = tag.keys()
		if "title" in keys:
			title = tag["title"][0]
		else:
			title = os.path.basename(filepath)

		if "artist" in keys:
			artist = tag["artist"][0]
		else:
			artist = "Unknown"

		if "performer" in keys:
			artist = tag["performer"][0]

		artist = format_artist_name(artist)

		if "album" in keys:
			album = tag["album"][0]
		else:
			album = "Unknown"

		if "genre" in keys:
			genre = tag["genre"][0]
		else:
			genre = "Unknown"

		length = int(tag.info.length)

		if "tracknumber" in keys:
			string = tag["tracknumber"][0]
			if "/" in string:
				index = string.find("/")
				tracknumber = int(string[0:index])
			else:
				tracknumber = int(string)
		else:
			tracknumber = 0
		
		if "date" in keys:
			string = tag["date"][0]
			if "-" in string:
				index = string.find("-")
				year = string[0:index]
			else:
				year = string
				
		else:
			year = 0
		if not year: year = 0

		# Get artist id, add it if missing
		artist_id = self._db.get_artist_id_by_name(artist)
		if artist_id == -1:
			self._db.add_artist(artist)
			artist_id = self._db.get_artist_id_by_name(artist)

		# Get genre id, add genre if missing
		genre_id = self._db.get_genre_id_by_name(genre)
		if genre_id == -1:
			self._db.add_genre(genre)
			genre_id = self._db.get_genre_id_by_name(genre)

		# Get album id, add it if missing
		album_id = self._db.get_album_id(album, artist_id, genre_id)
		if album_id == -1:
			self._db.add_album(album, artist_id, genre_id, int(year), path)
			album_id = self._db.get_album_id(album, artist_id, genre_id)

		# Add track to db
		self._db.add_track(title, filepath, length, tracknumber, artist_id, album_id)
