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

"""
	This is global object initialised at lollypop start
	member init order is important!
"""
class Objects_:
	def __init__(self):
		self.settings = None
		self.db = None
		self.sql = None
		self.albums = None
		self.artists = None
		self.genres = None
		self.tracks = None
		self.player = None
		self.art = None

Objects = Objects_()

ART_SIZE_MONSTER = 500
ART_SIZE_BIG = 200
ART_SIZE_MEDIUM = 48
ART_SIZE_SMALL = 32

SHUFFLE_ARTIST = 0
SHUFFLE_ALBUMS = 1
SHUFFLE_POPULARS = 2
SHUFFLE_GENRE = 3

COMPILATIONS = -1
POPULARS = -2
ALL = -3
