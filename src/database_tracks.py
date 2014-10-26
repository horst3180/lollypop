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

from lollypop.config import Objects

"""
	All functions take a sqlite cursor as last parameter, set another one if you're in a thread
"""
class DatabaseTracks:
	def __init__(self):
		pass

	"""
		Add a new track to database
		arg: name as string, filepath as string, length as int, tracknumber as int, artist_id as int, album_id as int, mtime as int
	"""
	def add(self, name, filepath, length, tracknumber, artist_id, album_id, mtime, sql = None):
		if not sql:
			sql = Objects["sql"]
		sql.execute("INSERT INTO tracks (name, filepath, length, tracknumber, artist_id, album_id, mtime) VALUES (?, ?, ?, ?, ?, ?, ?)", (name, filepath, length, tracknumber, artist_id, album_id, mtime))
		
		
	"""
		Get track name for track id
		arg: Track id as int
		ret: Name as string
	"""
	def get_name(self, track_id, sql = None):
		if not sql:
			sql = Objects["sql"]
		result = sql.execute("SELECT name FROM tracks where rowid=?", (track_id,))
		v = result.fetchone()
		if v:
			return v[0]

		return ""

	"""
		Get album id for track id
		arg: track id as int
		ret: album id as int
	"""
	def get_album_id(self, track_id, sql = None):
		if not sql:
			sql = Objects["sql"]
		result = sql.execute("SELECT album_id FROM tracks where rowid=?", (track_id,))
		v = result.fetchone()
		if v:
			return v[0]

		return -1

	"""
		Get mtime for tracks
		WARNING: Should be called before anything is shown on screen
		arg: None
		ret: dict of {filepath as string: mtime as int}
	"""
	def get_mtimes(self, sql = None):
		if not sql:
			sql = Objects["sql"]
		mtimes = {}
		sql.row_factory = self._dict_factory
		result = sql.execute("SELECT filepath, mtime FROM tracks")
		for row in result:
			mtimes.update(row)
		sql.row_factory = None
		return mtimes


	"""
		Get all track informations for track id
		arg: Track id as int
		ret: Array of (name as string, filepath as string, length as int, tracknumber as int, album_id as int)]
	"""
	def get_infos(self, track_id, sql = None):
		if not sql:
			sql = Objects["sql"]
		tracks = []
		result = sql.execute("SELECT name, filepath, length, tracknumber, album_id FROM tracks WHERE rowid=?" , (track_id,))
		v = result.fetchone()
		if v:
			return v
		return ()
	
	"""
		Get artist name for track id
		arg: Track id as int
		ret: Artist name as string
	"""
	def get_artist_name(self, track_id, sql = None):
		if not sql:
			sql = Objects["sql"]
		result = sql.execute("SELECT artists.name from artists,tracks where tracks.rowid=? and tracks.artist_id=artists.rowid", (track_id,))
		v = result.fetchone()
		if v:
			return v[0]

		return _("Unknown")

	"""
		Get artist id for track id
		arg: Track id as int
		ret: Artist id as int
	"""
	def get_artist_id(self, track_id, sql = None):
		if not sql:
			sql = Objects["sql"]
		result = sql.execute("SELECT artists.rowid from artists,tracks where tracks.rowid=? and tracks.artist_id=artists.rowid", (track_id,))
		v = result.fetchone()
		if v:
			return v[0]

		return -1


	"""
		Get track filepath for track id
		arg: Track id as int
		ret: Filepath as string
	"""
	def get_path(self, track_id, sql = None):
		if not sql:
			sql = Objects["sql"]
		result = sql.execute("SELECT filepath FROM tracks where rowid=?", (track_id,))
		v = result.fetchone()
		if v:
			return v[0]

		return ""

	"""
		Get all tracks filepath
		arg: None
		ret: Array of filepath as string
	"""
	def get_paths(self, sql = None):
		if not sql:
			sql = Objects["sql"]
		tracks = []
		result = sql.execute("SELECT filepath FROM tracks;")
		for row in result:
			tracks += row
		return tracks

	"""
		Get track length for track id
		arg: Track id as int
		ret: length as int
	"""
	def get_length(self, id, sql = None):
		if not sql:
			sql = Objects["sql"]
		result = sql.execute("SELECT length FROM tracks where rowid=?", (id,))
		v = result.fetchone()
		if v:
			return v[0]

		return 0
		
	"""
		Return True if no tracks in db
	"""
	def is_empty(self, sql = None):
		if not sql:
			sql = Objects["sql"]
		result = sql.execute("SELECT COUNT(*) FROM tracks  LIMIT 1")
		v = result.fetchone()
		if v:
			return v[0] == 0

		return True
		
	"""
		Clean database deleting orphaned entries
		No commit needed
	"""
	def clean(self, sql = None):
		if not sql:
			sql = Objects["sql"]
		sql.execute("DELETE FROM albums WHERE NOT EXISTS (SELECT rowid FROM tracks where albums.rowid = tracks.album_id)")
		sql.execute("DELETE FROM artists WHERE NOT EXISTS (SELECT rowid FROM albums where artists.rowid = albums.artist_id)")
		sql.execute("DELETE FROM genres WHERE NOT EXISTS (SELECT rowid FROM albums where genres.rowid = albums.genre_id)")
		sql.commit()

	"""
		Search for tracks looking like string
		arg: string
		return: Arrays of (id as int, name as string)
	"""
	def search(self, string, sql = None):
		if not sql:
			sql = Objects["sql"]
		tracks = []
		result = sql.execute("SELECT rowid, name FROM tracks where name like ? LIMIT 100", ('%'+string+'%',))
		for row in result:
			tracks += (row,)
		return tracks

	"""
		Remove track
		arg: Track path as string
	"""
	def remove(self, path, sql = None):
		if not sql:
			sql = Objects["sql"]
		sql.execute("DELETE FROM tracks WHERE filepath=?", (path,))
	
#######################
# PRIVATE             #
#######################

	"""
		Sqlite row factory
	"""
	def _dict_factory(self, cursor, row):
		d = {}
		d[row[0]] = row[1]
		return d
