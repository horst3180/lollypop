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
    settings = None
    db = None
    sql = None
    albums = None
    artists = None
    genres = None
    tracks = None
    playlists = None
    player = None
    art = None


# Represent what to do on next track
class NextContext:
    STOP_NONE = 0    # Continue playback
    STOP_TRACK = 1   # Stop after current track
    STOP_ALBUM = 2   # Stop after current album
    STOP_ARTIST = 3  # Stop after current artist


class ArtSize_:
    SMALL = 32
    MEDIUM = 48
    BIG = 200
    MONSTER = 500


class Shuffle_:
    NONE = 0
    TRACKS = 1
    ALBUMS = 2


class Navigation_:
    COMPILATIONS = -1
    POPULARS = -2
    PLAYLISTS = -3
    ALL = -4
    DEVICES = -1000

Objects = Objects_()
ArtSize = ArtSize_()
Shuffle = Shuffle_()
Navigation = Navigation_()
