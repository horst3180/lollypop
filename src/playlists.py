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

from gi.repository import GLib, GObject

import os

from stat import S_ISREG, ST_MTIME, ST_MODE

from lollypop.define import Objects, PlayListType


# Playlists manager: add, remove, list, append, ...
class PlaylistsManager(GObject.GObject):
    __gsignals__ = {
        # Add or remove a playlist
        'playlists-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
        # Objects added/removed to/from playlist
        'playlist-changed': (GObject.SignalFlags.RUN_FIRST, None, (str,))
    }

    """
        Create a playlist for type
        @param t as PlayListType
    """
    def __init__(self, t):
        GObject.GObject.__init__(self)
        self._idx = {}
        if t == PlayListType.RADIO:
            self._PLAYLISTS_PATH = os.path.expanduser("~") +\
                     "/.local/share/lollypop/radios" 
        else:  # Music
           self._PLAYLISTS_PATH = os.path.expanduser("~") +\
                     "/.local/share/lollypop/playlists" 


        # Create playlists directory if missing
        if not os.path.exists(self._PLAYLISTS_PATH):
            try:
                os.mkdir(self._PLAYLISTS_PATH)
            except Exception as e:
                print("Lollypop::PlaylistsManager::init: %s" % e)
        self._init_idx()

    """
        Add a playlist (Thread safe)
        @param playlist name as str
        @param get file descriptor as bool
        @return file descriptor if 2nd param True
    """
    def add(self, playlist_name, get_desc=False):
        filename = self._PLAYLISTS_PATH + "/"+playlist_name + ".m3u"
        try:
            if os.path.exists(filename):
                changed = False
            else:
                changed = True
            f = open(filename, "w")
            f.write("#EXTM3U\n")
            if get_desc:
                return f
            else:
                f.close()
            # Add playlist to cache
            if changed:
                try:
                    max_idx = max(self._idx.keys())+1
                except:
                    max_idx = 0
                self._idx[max_idx] = playlist_name
                GLib.idle_add(self.emit, "playlists-changed")
        except Exception as e:
            print("PlaylistsManager::add: %s" % e)

    """
        Rename playlist (Thread safe)
        @param new playlist name as str
        @param old playlist name as str
    """
    def rename(self, new_name, old_name):
        try:
            os.rename(self._PLAYLISTS_PATH+"/"+old_name+".m3u",
                      self._PLAYLISTS_PATH+"/"+new_name+".m3u")
            for (idx, playlist) in self._idx.items():
                if playlist == old_name:
                    self._idx[idx] = new_name
                    break
            GLib.idle_add(self.emit, "playlists-changed")
        except Exception as e:
            print("PlaylistsManager::rename: %s" % e)

    """
        delete playlist (Thread safe)
        @param playlist name as str
    """
    def delete(self, playlist_name):
        try:
            os.remove(self._PLAYLISTS_PATH+"/"+playlist_name+".m3u")
            for (idx, playlist) in self._idx.items():
                if playlist == playlist_name:
                    del self._idx[idx]
                    break
            GLib.idle_add(self.emit, "playlists-changed")
        except Exception as e:
            print("PlaylistsManager::delete: %s" % e)

    """
        Return availables playlists
        @return array of (id, string)
    """
    def get(self):
        return sorted(self._idx.items(),
                      key=lambda item: item[1].lower())

    """
        Return 5 last modified playlist
        @return array of (id, string)
    """
    def get_last(self):
        playlists = []
        try:
            index = 0
            entries = []
            for filename in os.listdir(self._PLAYLISTS_PATH):
                stat = os.stat(self._PLAYLISTS_PATH+"/"+filename)
                if S_ISREG(stat[ST_MODE]):
                    entries.append((stat[ST_MTIME], filename))
            for cdate, filename in sorted(entries, reverse=True):
                if filename.endswith(".m3u"):
                    playlists.append(filename[:-4])
                    index += 1
                    # Break if 5 playlists is reached
                    if index >= 5:
                        break
        except Exception as e:
            print("Lollypop::PlaylistManager::get_last: %s" % e)
        return playlists

    """
        Return availables tracks for playlist
        @param playlist playlist_name as str
        @return array of track filepath as str
    """
    def get_tracks(self, playlist_name):
        tracks = []
        try:
            f = open(self._PLAYLISTS_PATH+"/"+playlist_name+".m3u", "r")
            for filepath in f:
                if filepath[0] == "/":
                    tracks.append(filepath[:-1])
            f.close()
        except Exception as e:
            print("PlaylistsManager::get_tracks: %s" % e)
        return tracks

    """
        Set playlist tracks (Thread safe)
        @param playlist name as str
        @param tracks path as [str]
    """
    def set_tracks(self, playlist_name, tracks_path):
        f = self.add(playlist_name, True)
        for filepath in tracks_path:
            self._add_track(f, playlist_name, filepath)
        GLib.timeout_add(1000, self.emit, "playlist-changed", playlist_name)
        try:
            f.close()
        except Exception as e:
            print("PlaylistsManager::set_tracks: %s" % e)

    """
        Return availables tracks id for playlist
        Thread safe if you pass an sql cursor
        @param playlist name as str
        @return array of track id as int
    """
    def get_tracks_id(self, playlist_name, sql=None):
        tracks_id = []
        for filepath in self.get_tracks(playlist_name):
            tracks_id.append(Objects.tracks.get_id_by_path(filepath, sql))
        return tracks_id

    """
        Add track to playlist if not already present
        @param playlist name as str
        @param track filepath as str
    """
    def add_track(self, playlist_name, filepath):
        self._add_track(playlist_name, filepath)
        GLib.idle_add(self.emit, "playlist-changed", playlist_name)

    """
        Add tracks to playlist if not already present
        @param playlist name as str
        @param tracks filepath as [str]
    """
    def add_tracks(self, playlist_name, tracks_path):
        try:
            f = open(self._PLAYLISTS_PATH+"/"+playlist_name+".m3u", "a")
            for filepath in tracks_path:
                self._add_track(f, playlist_name, filepath)
            GLib.idle_add(self.emit, "playlist-changed", playlist_name)
            f.close()
        except Exception as e:
                print("PlaylistsManager::add_tracks: %s" % e)

    """
        Remove tracks from playlist
        @param playlist name as str
        @param tracks to remove as [str]
    """
    def remove_tracks(self, playlist_name, tracks_to_remove):
        playlist_tracks = self.get_tracks(playlist_name)
        self._remove_tracks(playlist_name, playlist_tracks, tracks_to_remove)
        GLib.idle_add(self.emit, "playlist-changed", playlist_name)

    """
        Return True if object_id is already present in playlist
        @param playlist name as str
        @param object id as int
        @param genre id as int
        @param is an album as bool
        @param sql as sqlite cursor
        @return bool
    """
    def is_present(self, playlist_name, object_id,
                   genre_id, is_album, sql=None):
        playlist_paths = self.get_tracks(playlist_name)
        if is_album:
            tracks_path = Objects.albums.get_tracks_path(object_id,
                                                         genre_id,
                                                         sql)
        else:
            tracks_path = [Objects.tracks.get_path(object_id, sql)]

        found = 0
        len_tracks = len(tracks_path)
        for filepath in tracks_path:
            if filepath in playlist_paths:
                found += 1
                if found >= len_tracks:
                    break
        if found == len_tracks:
            return True
        else:
            return False

#######################
# PRIVATE             #
#######################
    """
        Create initial index
    """
    def _init_idx(self):
        playlists = []
        try:
            for filename in sorted(os.listdir(self._PLAYLISTS_PATH)):
                if filename.endswith(".m3u"):
                    playlists.append(filename[:-4])
        except Exception as e:
            print("Lollypop::PlaylistManager::get: %s" % e)

        idx = 0
        for playlist in playlists:
            self._idx[idx] = playlist
            idx += 1

    """
        Add track to playlist if not already present
        @param f as file descriptor
        @param playlist name as str
        @param track filepath as str
    """
    def _add_track(self, f, playlist_name, filepath):
        tracks = self.get_tracks(playlist_name)
        # Do nothing if uri already present in playlist
        if filepath not in tracks:
            try:
                f.write(filepath+'\n')
            except Exception as e:
                print("PlaylistsManager::_add_track: %s" % e)

    """
        Remove track from playlist
        @param playlist name as str
        @param playlist tracks as [str]
        @param tracks to remove as [str]
    """
    def _remove_tracks(self, playlist_name, playlist_tracks, tracks_to_remove):
        try:
            f = open(self._PLAYLISTS_PATH+"/"+playlist_name+".m3u", "w")
            for path in playlist_tracks:
                if path not in tracks_to_remove:
                    f.write(path+'\n')
            f.close()
        except Exception as e:
            print("PlaylistsManager::remove_tracks: %s" % e)
