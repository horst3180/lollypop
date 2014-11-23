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

from gettext import gettext as _

from lollypop.config import *

"""
	All functions take a sqlite cursor as last parameter, set another one if you're in a thread
"""
class DatabaseArtists:
	def __init__(self):
		pass
		
	"""
		Add a new artist to database
		@param Artist name as string
	"""
	def add(self, name, sql = None):
		if not sql:
			sql = Objects["sql"]
		sql.execute("INSERT INTO artists (name) VALUES (?)", (name,))

	"""
		Get artist id
		@param Artist name as string
		@return Artist id as int
	"""
	def get_id(self, name, sql = None):
		if not sql:
			sql = Objects["sql"]

		result = sql.execute("SELECT rowid from artists where name=?", (name,))
		v = result.fetchone()
		if v and len(v) > 0:
			return v[0]

		return COMPILATIONS

	"""
		Get artist name
		@param Artist id as int
		@return Artist name as string
	"""
	def get_name(self, artist_id, sql = None):
		if not sql:
			sql = Objects["sql"]
		if artist_id == COMPILATIONS:
			return _("Many artists")

		result = sql.execute("SELECT name from artists where rowid=?", (artist_id,))
		v = result.fetchone()
		if v and len(v) > 0:
			return v[0]

		return _("Unknown")

	"""
		Get all availables albums  for artist
		@return Array of id as int
	"""
	def get_albums(self, artist_id, sql = None):
		if not sql:
			sql = Objects["sql"]
		albums = []
		result = sql.execute("SELECT rowid FROM albums where artist_id=? order by year",(artist_id,))
		for row in result:
			albums += row
		return albums


	"""
		Get all available artists
		
		@param None
		or
		@param Filter genre id as int
		
		@return Array of (artist id as int, artist name as string)
	"""
	def get_ids(self, genre_id, sql = None):
		if not sql:
			sql = Objects["sql"]
		artists = []
		result = []
		if genre_id == ALL:
			# Only artist that really have an album
			result = sql.execute("SELECT rowid, name FROM artists WHERE EXISTS (SELECT rowid FROM albums where albums.artist_id = artists.rowid) ORDER BY name COLLATE NOCASE")
		else:
			result = sql.execute("SELECT DISTINCT artists.rowid, artists.name FROM artists,albums WHERE artists.rowid == albums.artist_id AND albums.genre_id=? ORDER BY artists.name COLLATE NOCASE", (genre_id,))
		
		for row in result:
			artists += (row,)
		return artists
		
	"""
		Search for artists looking like string
		@param string
		@return Array of id as int
	"""
	def search(self, string, sql = None):
		if not sql:
			sql = Objects["sql"]
		artists = []
		result = sql.execute("SELECT rowid FROM artists where name like ? LIMIT 100", ('%'+string+'%',))
		for row in result:
			artists += row
		return artists
