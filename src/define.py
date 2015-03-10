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

# This is global object initialised at lollypop start
# member init order is important!


class Objects_:
    def __init__(self):
        self.settings = None
        self.db = None
        self.sql = None
        self.albums = None
        self.artists = None
        self.genres = None
        self.tracks = None
        self.playlists = None
        self.player = None
        self.art = None


class ArtSize_:
    def __init__(self):
        self.SMALL = 32
        self.MEDIUM = 48
        self.BIG = 200
        self.MONSTER = 500


class Shuffle_:
    def __init__(self):
        self.NONE = 0
        self.TRACKS = 1
        self.ALBUMS = 2


class Navigation_:
    def __init__(self):
        self.COMPILATIONS = -1
        self.POPULARS = -2
        self.PLAYLISTS = -3
        self.ALL = -4
        self.DEVICES = -1000

Objects = Objects_()
ArtSize = ArtSize_()
Shuffle = Shuffle_()
Navigation = Navigation_()
