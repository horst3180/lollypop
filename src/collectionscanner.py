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

import os
from time import sleep
import sqlite3
from gettext import gettext as _, ngettext    
from gi.repository import GLib, Gdk, GObject
from _thread import start_new_thread
import mutagen

from lollypop.config import *
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
	_mimes = [ "mp3", "ogg", "flac", "m4a", "mp4", "opus" ]
	def __init__(self):
		GObject.GObject.__init__(self)

		self._in_thread = False
		self._progress = None
		self._smooth = False
		self._popularities = Objects["db"].get_popularities()

	"""
		Update database
		@param progress as Gtk.Progress
		@param smooth as bool, if smooth, try to scan smoothly
	"""
	def update(self,  progress, smooth):
		self._smooth = smooth
		paths = Objects["settings"].get_value('music-path')
		if len(paths) == 0:
			if GLib.get_user_special_dir(GLib.USER_DIRECTORY_MUSIC):
				paths = [ GLib.get_user_special_dir(GLib.USER_DIRECTORY_MUSIC) ]
			else:
				print("You need to add a music path to org.gnome.Lollypop in dconf")

		if not self._in_thread:
			self._progress = progress
			progress.show()
			self._in_thread = True
			self._compilations = []
			self._mtimes = Objects["tracks"].get_mtimes()
			start_new_thread(self._scan, (paths,))

#######################
# PRIVATE             #
#######################

	"""
		Update progress bar status
		@param scanned items as int, total items as int
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
		@param paths as [string], paths to scan
	"""
	def _scan(self, paths):
		sql = Objects["db"].get_cursor()

		tracks = Objects["tracks"].get_paths(sql)
		new_tracks = []
		count = 0
		for path in paths:
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
				print(filepath)
				print("CollectionScanner::_scan(): %s" %e)
			i += 1
			if self._smooth:
				sleep(0.001)

		# Clean deleted files
		if i > 0:
			for track in tracks:
				Objects["tracks"].remove(track, sql)

		Objects["tracks"].clean(sql)
		sql.commit()
		sql.close()
		GLib.idle_add(self._notify)



	"""
		Add new file to db with tag
		@param filepath as string, file modification time as int, tag as mutagen.File(easy=True), sql as sqlite cursor
	"""
	def _add2db(self, filepath, mtime, tag, sql):
		compilation = False
		path = os.path.dirname(filepath)
		keys = tag.keys()
		if "title" in keys:
			title = tag["title"][0]
		else:
			title = os.path.basename(filepath)

		if "artist" in keys:
			artist = format_artist_name(tag["artist"][0])
		else:
			artist = "Unknown"

		if "performer" in keys:
			performer = format_artist_name(tag["performer"][0])	
		else:
			performer = None

		if "album" in keys:
			album = tag["album"][0]
		else:
			album = "Unknown"

		if "genre" in keys:
			genre = tag["genre"][0]
		else:
			genre = "Unknown"

		length = int(tag.info.length)

		
		if "discnumber" in keys:
			string = tag["discnumber"][0]
			if "/" in string:
				index = string.find("/")
				discnumber = int(string[0:index])
			else:
				try:
					discnumber = int(string)
				except:
					discnumber = 0
		else:
			discnumber = 0
		
		if "tracknumber" in keys:
			string = tag["tracknumber"][0]
			if "/" in string:
				index = string.find("/")
				tracknumber = int(string[0:index])
			else:
				try:
					tracknumber = int(string)
				except:
					tracknumber = 0
		else:
			tracknumber = 0
		
		if "date" in keys:
			try:
				string = tag["date"][0]
				if "-" in string:
					index = string.find("-")
					year = int(string[0:index])
				else:
					year = int(string)
			except:
				year = 0
		else:
			year = 0

		# Get artist id, add it if missing
		artist_id = Objects["artists"].get_id(artist, sql)
		if artist_id == COMPILATIONS:
			Objects["artists"].add(artist, sql)
			artist_id = Objects["artists"].get_id(artist, sql)
	
		if performer:
			# Get performer id, add it if missing
			performer_id = Objects["artists"].get_id(performer, sql)
			if performer_id == COMPILATIONS:
				Objects["artists"].add(performer, sql)
				performer_id = Objects["artists"].get_id(performer, sql)
		else:
			performer_id = COMPILATIONS

		# Get genre id, add genre if missing
		genre_id = Objects["genres"].get_id(genre, sql)
		if genre_id == -1:
			Objects["genres"].add(genre, sql)
			genre_id = Objects["genres"].get_id(genre, sql)


		#
		# Here we search an existing album for this track
		#
		# Get albums with this name from this artist/performer
		if performer_id != COMPILATIONS:
			album_id = Objects["albums"].get_id(album, performer_id, genre_id, sql)
		else:
			album_id = Objects["albums"].get_id(album, artist_id, genre_id, sql)

		# Track can go in a compilation
		if performer_id == COMPILATIONS and album_id == -1:
			# Look if we find a compilation for this name:
			album_id = Objects["albums"].get_id(album, COMPILATIONS, genre_id, sql)
			if album_id == -1:
				# Search for others album with same name
				for album_id_ in Objects["albums"].get_id(album, None, genre_id, sql): 
					# there is no performer tag, so use it
					if len(Objects["albums"].get_performers_id(album_id_, sql)) == 0:
						album_id = album_id_
						# We need to check if it's an album without performers or 
						# a compilation ie different artists without performers
						for track_id_ in Objects["albums"].get_tracks(album_id, sql):
							artist_id_ = Objects["tracks"].get_artist_id(track_id_, sql)
							if artist_id_ != artist_id:
								# Mark it as a compilation
								Objects["albums"].set_artist_id(album_id, COMPILATIONS, sql)
								break

		popularity = 0
		if path in self._popularities:
			popularity = self._popularities[path]
		# Get a new album if none found
		if album_id == -1:
			if performer_id != COMPILATIONS:
				Objects["albums"].add(album, performer_id, genre_id, year, path, popularity, sql)
				album_id = Objects["albums"].get_id(album, performer_id, genre_id, sql)
			else:
				Objects["albums"].add(album, artist_id, genre_id, year, path, popularity, sql)
				album_id = Objects["albums"].get_id(album, artist_id, genre_id, sql)

		# Now we have our album id, check if path doesn't change
		if Objects["albums"].get_path(album_id, sql) != path:
			Objects["albums"].set_path(album_id, path, sql)

		# Add track to db
		Objects["tracks"].add(title, filepath, length, tracknumber, discnumber, artist_id, performer_id, album_id, mtime, sql)
