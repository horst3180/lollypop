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

from gi.repository import Gdk

# This is a multimedia device
class Device:
    def __init__(self):
        self.id = None
        self.name = None
        self.path = None

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

Objects = Objects_()

# We want 500 and 200 in full hd
ART_SIZE_MONSTER = int(500*Gdk.Screen.get_default().get_width()/1920)
ART_SIZE_BIG = int(200*Gdk.Screen.get_default().get_width()/1920)
ART_SIZE_MEDIUM = 48
ART_SIZE_SMALL = 32

SHUFFLE_NONE = 0
SHUFFLE_TRACKS = 1
SHUFFLE_ALBUMS = 2

COMPILATIONS = -1
POPULARS = -2
PLAYLISTS = -3
ALL = -4
DEVICES = -1000
