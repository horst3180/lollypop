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

from gettext import gettext as _
import sqlite3
import os
from gi.repository import Gtk, GLib

from lollypop.config import Objects
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
	#create_sort_index = '''CREATE INDEX tracknumber ON tracks(tracknumber DESC)'''
							   
	def __init__(self):
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
		# Create db schema
		try:
			sql.execute(self.create_albums)
			sql.execute(self.create_artists)
			sql.execute(self.create_genres)
			sql.execute(self.create_tracks)
			#sql.execute(self.create_sort_index)
			sql.commit()
			Objects["settings"].set_value('db-version', GLib.Variant('i', upgrade.count()))
			sql.close()
		# Upgrade db schema
		except:
			try:
				db_version = Objects["settings"].get_value('db-version')
				upgrade = DatabaseUpgrade(sql, db_version)
				if db_version.get_int32() < upgrade.count():
					Objects["settings"].set_value('db-version', GLib.Variant('i', upgrade.do_db_upgrade()))
			except Exception as e:
				print(e)
				pass
			sql.close()

	def get_cursor(self):
		return sqlite3.connect(self.DB_PATH)

	
