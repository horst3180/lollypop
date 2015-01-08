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

from gettext import gettext as _
import sqlite3
import os
from gi.repository import Gtk, GLib

from lollypop.define import Objects
from lollypop.database_upgrade import DatabaseUpgrade
from lollypop.database_albums import DatabaseAlbums
from lollypop.database_artists import DatabaseArtists
from lollypop.database_genres import DatabaseGenres
from lollypop.database_tracks import DatabaseTracks


class Database:

	LOCAL_PATH = os.path.expanduser ("~") +  "/.local/share/lollypop"
	DB_PATH = "%s/lollypop.db" % LOCAL_PATH

	create_albums = '''CREATE TABLE albums (name TEXT NOT NULL,
						artist_id INT NOT NULL,
						genre_id INT NOT NULL,
						year INT NOT NULL,
						path TEXT NOT NULL,
						md5 TEXT,
						popularity INT NOT NULL)'''
	create_artists = '''CREATE TABLE artists (name TEXT NOT NULL)'''
	create_genres = '''CREATE TABLE genres (name TEXT NOT NULL)'''
	create_tracks = '''CREATE TABLE tracks (name TEXT NOT NULL,
						filepath TEXT NOT NULL,
						length INT,
						tracknumber INT,
						discnumber INT,
						artist_id INT NOT NULL,
						performer_id INT NOT NULL,
						album_id INT NOT NULL,
						mtime INT)'''
	   
	"""
		Create database tables or manage update if needed
	"""
	def __init__(self):
		self._popularity_backup = {}
		# Create db directory if missing
		if not os.path.exists(self.LOCAL_PATH):
			try:
				os.mkdir(self.LOCAL_PATH)
			except:
				print("Can't create %s" % self.LOCAL_PATH)
		try:		
			sql = self.get_cursor()
			
		except:
			exit(-1)
			
		db_version = Objects.settings.get_value('db-version')
		upgrade = DatabaseUpgrade(sql, db_version)
		# Create db schema
		try:
			sql.execute(self.create_albums)
			sql.execute(self.create_artists)
			sql.execute(self.create_genres)
			sql.execute(self.create_tracks)
			sql.commit()
			Objects.settings.set_value('db-version', GLib.Variant('i', upgrade.count()))
		# Upgrade db schema
		except:
			try:
				if db_version.get_int32() < upgrade.count():
					Objects.settings.set_value('db-version', GLib.Variant('i', upgrade.do_db_upgrade()))
				if upgrade.reset_needed():
					self._set_popularities(sql)
					Objects.settings.set_value('party-ids', GLib.Variant('ai', []))
					sql.execute("DELETE FROM tracks")
					sql.execute("DELETE FROM albums")
					sql.execute("DELETE FROM artists")
					sql.execute("DELETE FROM genres")
					sql.commit()
			except Exception as e:
				print(e)
				pass
		sql.close()


	"""
		Get a dict with album path and popularity
		This is usefull for collection scanner be able to restore popularities after db reset
	"""
	def get_popularities(self):
		return self._popularity_backup

#########
#Private#
#########

	"""
		Set a dict with album path and popularity
		This is usefull for collection scanner be able to restore popularities after db reset 
	"""
	def _set_popularities(self, sql):
		result = sql.execute("SELECT path, popularity FROM albums")
		for row in result:
			self._popularity_backup[row[0]] = row[1]

	"""
		Return a new sqlite cursor
	"""
	def get_cursor(self):
		return sqlite3.connect(self.DB_PATH)

	
