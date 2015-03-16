#!/usr/bin/python
# Copyright (c) 2014-2015 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from lollypop.define import Objects, Navigation


# All functions take a sqlite cursor as last parameter,
# set another one if you're in a thread
class DatabaseArtists:
    def __init__(self):
        pass

    """
        Add a new artist to database
        @param Artist name as string
        @warning: commit needed
    """
    def add(self, name, sql=None):
        if not sql:
            sql = Objects.sql
        sql.execute("INSERT INTO artists (name) VALUES (?)",
                    (name,))

    """
        Get artist id
        @param Artist name as string
        @return Artist id as int
    """
    def get_id(self, name, sql=None):
        if not sql:
            sql = Objects.sql

        result = sql.execute("SELECT rowid from artists\
                              WHERE name=?", (name,))
        v = result.fetchone()
        if v and len(v) > 0:
            return v[0]

        return None

    """
        Get artist name
        @param Artist id as int
        @return Artist name as string
    """
    def get_name(self, artist_id, sql=None):
        if not sql:
            sql = Objects.sql
        if artist_id == Navigation.COMPILATIONS:
            return _("Many artists")

        result = sql.execute("SELECT name from artists WHERE rowid=?",
                             (artist_id,))
        v = result.fetchone()
        if v and len(v) > 0:
            return v[0]

        return _("Unknown")

    """
        Get all availables albums  for artist
        @return Array of id as int
    """
    def get_albums(self, artist_id, sql=None):
        if not sql:
            sql = Objects.sql
        albums = []
        result = sql.execute("SELECT rowid FROM albums\
                              WHERE artist_id=?\
                              ORDER BY year", (artist_id,))
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
    def get(self, genre_id, sql=None):
        if not sql:
            sql = Objects.sql
        artists = []
        result = []
        if genre_id == Navigation.ALL or genre_id is None:
            # Only artist that really have an album
            result = sql.execute("SELECT rowid, name FROM artists\
                                  WHERE EXISTS\
                                    (SELECT rowid FROM albums\
                                     WHERE albums.artist_id = artists.rowid)\
                                  ORDER BY name COLLATE NOCASE")
        else:
            result = sql.execute("SELECT DISTINCT artists.rowid, artists.name\
                                  FROM artists, albums, albums_genres\
                                  WHERE artists.rowid == albums.artist_id\
                                  AND albums_genres.genre_id=?\
                                  AND albums_genres.album_id=albums.rowid\
                                  ORDER BY artists.name\
                                  COLLATE NOCASE", (genre_id,))

        for row in result:
            artists += (row,)
        return artists

    """
        Return True if artist exist
        @param artist id as int
    """
    def exists(self, artist_id, sql=None):
        if not sql:
            sql = Objects.sql

        result = sql.execute("SELECT COUNT(*) from artists WHERE rowid=?",
                             (artist_id,))
        v = result.fetchone()
        if v and len(v) > 0:
            return bool(v[0])

        return False

    """
        Search for artists looking like string
        @param string
        @return Array of id as int
    """
    def search(self, string, sql=None):
        if not sql:
            sql = Objects.sql
        artists = []
        result = sql.execute("SELECT rowid FROM artists\
                              WHERE name LIKE ?\
                              LIMIT 25", ('%'+string+'%',))
        for row in result:
            artists += row
        return artists
