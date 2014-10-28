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

import os
from time import sleep
import sqlite3
from gettext import gettext as _, ngettext    
from gi.repository import GLib, Gdk, GObject
from _thread import start_new_thread
import mutagen

from lollypop.config import Objects
from lollypop.utils import format_artist_name
from lollypop.database import Database
from lollypop.database_albums import DatabaseAlbums
from lollypop.database_artists import DatabaseArtists
from lollypop.database_genres import DatabaseGenres
from lollypop.database_tracks import DatabaseTracks

class CollectionScanner(GObject.GObject):
	__gsignals__ = {
		'scan-finished': (GObject.SIGNAL_RUN_FIRST, None, ()),
	}
	_mimes = [ "mp3", "ogg", "flac", "m4a", "mp4" ]
	def __init__(self, paths):
		GObject.GObject.__init__(self)

		self._in_thread = False
		self._progress = None

		if len(paths) > 0:
			self._paths = paths
		else:
			self._paths = [ GLib.get_user_special_dir(GLib.USER_DIRECTORY_MUSIC) ]

	"""
		Update database
	"""
	def update(self,  progress):
		self._progress = progress
		progress.show()
		if not self._in_thread:
			self._in_thread = True
			self._mtimes = Objects["tracks"].get_mtimes()
			start_new_thread(self._scan, ())

#######################
# PRIVATE             #
#######################

	"""
		Update progress bar
	"""
	def _update_progress(self, current, total):
		self._progress.set_fraction(current/total)
		
	"""
		Notify from main thread when scan finished
	"""
	def _notify(self):
		self._in_thread = False
		self._progress.hide()
		self.emit("scan-finished")
		
	"""
		Scan music collection for music files
	"""
	def _scan(self):
		sql = Objects["db"].get_cursor()

		tracks = Objects["tracks"].get_paths(sql)
		new_tracks = []
		count = 0
		for path in self._paths:
			for root, dirs, files in os.walk(path):
				for f in files:
					lowername = f.lower()
					supported = False
					for mime in self._mimes:
						if lowername.endswith(mime):
							supported = True
							break	
					if supported:
						new_tracks.append(os.path.join(root, f))
						count += 1

		i = 0
		for filepath in new_tracks:
			GLib.idle_add(self._update_progress, i, count)
			mtime = int(os.path.getmtime(filepath))
			try:
				if filepath not in tracks:
					tag = mutagen.File(filepath, easy = True)
					self._add2db(filepath, mtime, tag, sql)
				else:
					# Update tags by removing song and readd it
					if mtime != self._mtimes[filepath]:
						tag = mutagen.File(filepath, easy = True)
						Objects["tracks"].remove(filepath, sql)
						self._add2db(filepath, mtime, tag, sql)
					tracks.remove(filepath)
			
			except Exception as e:
				print("CollectionScanner::_scan(): %s" %e)
			i += 1

		# Clean deleted files
		for track in tracks:
			Objects["tracks"].remove(track, sql)

		Objects["tracks"].clean(sql)
		Objects["albums"].compilation_lookup(sql)
		sql.commit()
		sql.close()
		GLib.idle_add(self._notify)



	"""
		Add new file to db with tag
	"""
	def _add2db(self, filepath, mtime, tag, sql):
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
		artist_id = Objects["artists"].get_id(artist, sql)
		if artist_id == -1:
			Objects["artists"].add(artist, sql)
			artist_id = Objects["artists"].get_id(artist, sql)

		# Get genre id, add genre if missing
		genre_id = Objects["genres"].get_id(genre, sql)
		if genre_id == -1:
			Objects["genres"].add(genre, sql)
			genre_id = Objects["genres"].get_id(genre, sql)

		# Get album id, add it if missing
		album_id = Objects["albums"].get_id_var(album, artist_id, genre_id, sql)
		if album_id == -1:
			Objects["albums"].add(album, artist_id, genre_id, int(year), path, sql)
			album_id = Objects["albums"].get_id_var(album, artist_id, genre_id, sql)

		# Add track to db
		Objects["tracks"].add(title, filepath, length, tracknumber, artist_id, album_id, mtime, sql)
