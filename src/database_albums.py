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
class DatabaseAlbums:
	def __init__(self):
		pass
		
	"""
		Add a new album to database
		arg: Album name as string, artist id as int, genre id as int, year as int, path as string
	"""
	def add(self, name, artist_id, genre_id, year, path):
		if not sql:
			sql = Objects["sql"]
		sql.execute("INSERT INTO albums (name, artist_id, genre_id, year, path, popularity)\
		                   VALUES (?, ?, ?, ?, ?, ?)",  (name, artist_id, genre_id, year, path, 0))
		                   
	"""
		Increment popularity field for album id
		No commit needed
		arg: int
	"""
	def set_more_popular(self, album_id, sql = None):
		if not sql:
			sql = Objects["sql"]
		result = sql.execute("SELECT popularity from albums WHERE rowid=?", (album_id,))
		pop = result.fetchone()
		if pop:
			current = pop[0]
		else:
			current = 0
		current += 1
		sql.execute("UPDATE albums set popularity=? WHERE rowid=?", (current, album_id))
		sql.commit()

	"""
		Get album id 
		
		args: Album name as string, artist id as int and genre id as int
		or
		args: Track id as int


		ret: Album id as int
	"""
	def get_id(self,*args, sql = None):
		if not sql:
			sql = Objects["sql"]
		if len(args) == 1:
			result = sql.execute("SELECT albums.rowid FROM albums,tracks where tracks.album_id=albums.rowid AND tracks.rowid=?", (args[0],))
			v = result.fetchone()
			if v:
				return v[0]
		elif len(args) == 3:
			result = sql.execute("SELECT rowid FROM albums where name=? AND artist_id=? AND genre_id=?", (args[0], args[1], args[2]))
			v = result.fetchone()
			if v:
				return v[0]
	
		return -1

	"""
		Get genre id
		arg: Album id as int
		ret: Genre id as int
	"""
	def get_genre(self, album_id, sql = None):
		if not sql:
			sql = Objects["sql"]
		result = sql.execute("SELECT genre_id FROM albums WHERE rowid=?", (album_id,))
		v = result.fetchone()
		if v:
			return v[0]

		return -1

	"""
		Get album name for album id
		arg: Album id as int
		ret: Album name as string
	"""
	def get_name(self, album_id, sql = None):
		if not sql:
			sql = Objects["sql"]
		result = sql.execute("SELECT name FROM albums where rowid=?", (album_id,))
		v = result.fetchone()
		if v:
			return v[0]

		return _("Unknown")

	"""
		Get artist name
		arg: Album id as int
		ret: Artist name as string
	"""
	def get_artist_name(self, album_id, sql = None):
		if not sql:
			sql = Objects["sql"]
		result = sql.execute("SELECT artists.name from artists,albums where albums.rowid=? AND albums.artist_id == artists.rowid", (album_id,))
		v = result.fetchone()
		if v:
			return v[0]

		return _("Compilation")

	"""
		Get artist id
		arg: Album id as int
		ret: Artist id as int
	"""
	def get_artist_id(self, album_id, sql = None):
		if not sql:
			sql = Objects["sql"]
		result = sql.execute("SELECT artists.rowid from artists,albums where albums.rowid=? AND albums.artist_id == artists.rowid", (album_id,))
		v = result.fetchone()
		if v:
			return v[0]

		return -1
	"""
		Get album year for album id
		arg: Album id as int
		ret: Album year as string
	"""
	def get_year(self, album_id, sql = None):
		if not sql:
			sql = Objects["sql"]
		result = sql.execute("SELECT year FROM albums where rowid=?", (album_id,))
		v = result.fetchone()
		if v:
			if v[0]:
				return str(v[0])

		return ""

	"""
		Get album path for album id
		arg: Album id as int
		ret: Album path as string
	"""
	def get_path(self, album_id, sql = None):
		if not sql:
			sql = Objects["sql"]
		result = sql.execute("SELECT path FROM albums where rowid=?", (album_id,))
		v = result.fetchone()
		if v:
			return v[0]

		return ""
	
	"""
		Get albums ids with popularity
		arg: None
		ret: Array of album ids as int
	"""
	def get_populars(self, sql = None):
		if not sql:
			sql = Objects["sql"]
		albums = []
		result = sql.execute("SELECT rowid FROM albums where popularity!=0 ORDER BY popularity DESC LIMIT 100")
		for row in result:
			albums += row
		return albums

	"""
		Get album ids for party mode based on genre ids
		arg: Array of genre ids
		ret: Array of album ids as int
	"""
	def get_party_ids(self, genre_ids, sql = None):
		if not sql:
			sql = Objects["sql"]
		albums = []
		# get popular first
		if -1 in genre_ids:
			albums = self.get_populars()
		for genre_id in genre_ids:
			for album in Objects["genres"].get_albums(genre_id, sql):
				if album not in albums:
					albums.append(album)
		return albums

	"""
		Get number of tracks in an album
		arg: Album id as int
		ret: count as int
	"""
	def get_count(self, album_id, sql = None):
		if not sql:
			sql = Objects["sql"]
		result = sql.execute("SELECT COUNT(*) FROM tracks where album_id=?", (album_id,))
		v = result.fetchone()
		if v:
			return v[0]
		return -1

	"""
		Get tracks for album id
		arg: Album id as int
		ret: Arrays of tracks id as int
	"""
	def get_tracks(self, album_id, sql = None):
		if not sql:
			sql = Objects["sql"]
		tracks = []
		result = sql.execute("SELECT rowid FROM tracks WHERE album_id=? ORDER BY tracknumber" , (album_id,))
		for row in result:
			tracks += row
		return tracks

	"""
		Get tracks informations for album id
		arg: Album id as int
		ret: Arrays of (tracks id as int, name as string, filepath as string, length as int)
	"""
	def get_tracks_infos(self, album_id, sql = None):
		if not sql:
			sql = Objects["sql"]
		tracks = []
		result = sql.execute("SELECT rowid, name, filepath, length FROM tracks WHERE album_id=? ORDER BY tracknumber" , (album_id,))
		for row in result:
			tracks += (row,)
		return tracks


	"""
		Get albums ids
		
		arg: None
		or
		arg: Artist id as int/None, genre id as int/None
		
		ret: Array of album ids as int
	"""
	def get_ids(self, *args, sql = None):
		if not sql:
			sql = Objects["sql"]
		albums = []
		result = []
		if len(args) == 0:
			result = sql.execute("SELECT rowid FROM albums ORDER BY artist_id")
		elif len(args) == 2:
			if args[1] == None:
				result = sql.execute("SELECT rowid FROM albums WHERE artist_id=? ORDER BY year", (args[0],))
			elif args[0] == None:
				result = sql.execute("SELECT albums.rowid FROM albums, artists WHERE genre_id=? and artists.rowid=artist_id ORDER BY artists.name COLLATE NOCASE, albums.year", (args[1],))
			else:
				result = sql.execute("SELECT rowid FROM albums WHERE artist_id=? and genre_id=? ORDER BY year", (args[0], args[1]))
			
		for row in result:
			albums += row
		return albums

	"""
		Get all compilations
		
		arg: None
		or
		arg: genre id as int
		
		ret: Array of album ids as int
	"""
	def get_compilations(self, *args, sql = None):
		if not sql:
			sql = Objects["sql"]
		albums = []
		result = []
		if len(args) == 0:
			result = sql.execute("SELECT albums.rowid FROM albums WHERE artist_id=-1 ORDER BY albums.year")
		elif len(args) == 1:
			result = sql.execute("SELECT albums.rowid FROM albums WHERE genre_id=? and artist_id=-1 ORDER BY albums.year", (args[0],))
		for row in result:
			albums += row
		return albums


	"""
		Search for albums looking like string
		arg: string
		return: Array of (id as int, artist_id as int)
	"""
	def search(self, string, sql = None):
		if not sql:
			sql = Objects["sql"]
		albums = []
		result = sql.execute("SELECT rowid, artist_id FROM albums where name like ? LIMIT 100", ('%'+string+'%',))
		for row in result:
			albums += (row,)
		return albums

	"""
		Search for compilation in database, regroups albums
		No commit needed
	"""
	def compilation_lookup(self, sql = None):
		if not sql:
			sql = Objects["sql"]
		albums = []
		cursor = sql.execute("SELECT rowid, artist_id, path FROM albums")
		# Copy cursor to an array
		for rowid, artist_id, path in cursor:
			albums.append((rowid, artist_id, path))

		for rowid, artist_id, path in albums:
			compilation_set = False
			other_albums = sql.execute("SELECT rowid, artist_id, path FROM albums WHERE rowid!=? and artist_id!=? and path=?", (rowid,artist_id,path))
			for other_rowid, other_artist_id, other_path in other_albums:
				# Mark new albums as compilation (artist_id == -1)
				if  not compilation_set:
					sql.execute("UPDATE albums SET artist_id=-1 WHERE rowid=?", (rowid,))
					compilation_set = True
				# Add track to compilation, delete orphaned album
				tracks = sql.execute("SELECT rowid FROM tracks WHERE album_id=?", (other_rowid,))
				for track in tracks:
					sql.execute("UPDATE tracks SET album_id=? WHERE rowid=?", (rowid,track[0]))
				sql.execute("DELETE FROM albums WHERE rowid=?", (other_rowid,))
				albums.remove((other_rowid, other_artist_id, other_path))
		sql.commit()


