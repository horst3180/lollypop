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

from lollypop.define import *

"""
	All functions take a sqlite cursor as last parameter, set another one if you're in a thread
"""
class DatabasePlaylists:
	def __init__(self):
		pass

	"""
		Add a new playlist to database
		@param name as string
	"""
	def add(self, name, sql = None):
		if not sql:
			sql = Objects.sql
		sql.execute("INSERT INTO playlists (name) VALUES (?)", (name,))
		sql.commit()

	"""
		Delete playlist from database
		@param name as string
	"""
	def delete(self, name, sql = None):
		if not sql:
			sql = Objects.sql
		result = sql.execute("SELECT id from playlists WHERE name=?", (name,))
		v = result.fetchone()
		if v and len(v) > 0:		
			sql.execute("DELETE FROM playlists_ids WHERE playlist_id = ?", (v[0],))
		else:
			print("Fail to get playlist id for: ", playlist_name)
		sql.execute("DELETE FROM playlists WHERE name=?", (name,))
		sql.commit()

	"""
		Rename playlist
		@param name as str
		@param old name as str
	"""
	def rename(self, name, old_name, sql = None):
		if not sql:
			sql = Objects.sql
		result = sql.execute("UPDATE playlists set name=? WHERE name=?", (name, old_name))
		sql.commit()

	"""
		Add track to playlist
		@param track id as int
		@param playlist name as str
	"""
	def add_track(self, track_id, playlist_name, sql = None):
		if not sql:
			sql = Objects.sql
		result = sql.execute("SELECT rowid FROM playlists where name=?", (playlist_name,))
		v = result.fetchone()
		if v and len(v) > 0:		
			sql.execute("INSERT INTO playlists_ids (track_id, playlist_id) VALUES (?, ?)", (track_id, v[0]))
			sql.commit()
		else:
			print("Fail to get playlist id for: ", playlist_name)

	"""
		Remove track from playlist
		@param track id as int
		@param playlist name as str
	"""
	def remove_track(self, track_id, playlist_name, sql = None):
		if not sql:
			sql = Objects.sql
		result = sql.execute("SELECT rowid FROM playlists where name=?", (playlist_name,))
		v = result.fetchone()
		if v and len(v) > 0:		
			sql.execute("DELETE FROM playlists_ids WHERE track_id = ? AND  playlist_id = ?", (track_id, v[0]))
			sql.commit()
		else:
			print("Fail to get playlist id for: ", playlist_name)

	"""
		Get playlist name for playlist id
		@param Playlist id as int
		@return Name as string
	"""
	def get_name(self, playlist_id, sql = None):
		if not sql:
			sql = Objects.sql
		result = sql.execute("SELECT name FROM playlists where rowid=?", (playlist_id,))
		v = result.fetchone()
		if v and len(v) > 0:
			return v[0]

		return ""

	"""
		Get availables playlits
		@return array of str
	"""
	def get(self, sql = None):
		if not sql:
			sql = Objects.sql
		result = sql.execute("SELECT rowid, name from playlists ORDER BY name")
		playlists = []
		for row in result:
			playlists += (row,)
		return playlists

	"""
		Get tracks for playlist
		@param playlist name as str
		@return array of int
	"""
	def get_tracks(self, name, sql = None):
		if not sql:
			sql = Objects.sql
		result = sql.execute("SELECT track_id from playlists, playlists_ids WHERE playlists.name=? and playlists.rowid = playlists_ids.playlist_id", (name,))
		tracks = []
		for row in result:
			tracks += row
		return tracks
