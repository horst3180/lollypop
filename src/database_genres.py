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

from lollypop.define import Objects

"""
	All functions take a sqlite cursor as last parameter, set another one if you're in a thread
"""
class DatabaseGenres:
	def __init__(self):
		pass
	
	"""
		Add a new genre to database
		@param Name as string
	"""
	def add(self, name, sql = None):
		if not sql:
			sql = Objects.sql
		sql.execute("INSERT INTO genres (name) VALUES (?)", (name,))
		

	"""
		Get genre id for name
		@param name as string
		@return genre id as int
	"""
	def get_id(self, name, sql = None):
		if not sql:
			sql = Objects.sql
		result = sql.execute("SELECT rowid from genres where name=?", (name,))
		v = result.fetchone()
		if v and len(v) > 0:
			return v[0]

		return -1

	"""
		Get genre name for genre id
		@param string
		@return int
	"""
	def get_name(self, genre_id, sql = None):
		if not sql:
			sql = Objects.sql
		result = sql.execute("SELECT name from genres where rowid=?", (genre_id,))
		v = result.fetchone()
		if v and len(v) > 0:
			return v[0]

		return _("Unknown")


	"""
		Get all availables albums  for genres
		@return Array of id as int
	"""
	def get_albums(self, genre_id, sql = None):
		if not sql:
			sql = Objects.sql
		albums = []
		result = sql.execute("SELECT rowid FROM albums where genre_id=?",(genre_id,))
		for row in result:
			albums += row
		return albums

	"""
		Get all availables genres
		@return Array of (id as int, name as string)]
	"""
	def get_ids(self, sql = None):
		if not sql:
			sql = Objects.sql
		genres = []
		result = sql.execute("SELECT rowid, name FROM genres ORDER BY name COLLATE NOCASE")
		for row in result:
			genres += (row,)
		return genres


