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
from gi.repository import Gio
from _thread import start_new_thread

from lollypop.define import Objects, NextContext


# Show a contextual menu for object
class PopMainMenu(Gio.Menu):
    """
        Init menu model
        @param object id as int
        @param genre id as int
        @param is album as bool
        @param toolbar context as bool => only show playlists
        @param parent as Gtk.Widget
    """
    def __init__(self, object_id, genre_id, is_album, toolbar_context, parent):
        Gio.Menu.__init__(self)
        self._genre_id = genre_id
        self._is_album = is_album
        self._parent = parent
        app = Gio.Application.get_default()
        # FIXME How signal connect works when called many times

        playback_menu = Gio.Menu()
        if toolbar_context and not Objects.player.is_party():
            self._set_playback_actions(app, playback_menu, object_id)
        if not toolbar_context:
            self._set_queue_actions(app, playback_menu, object_id, is_album)
        self.insert_section(0, _("Playback"), playback_menu)

        playlist_menu = Gio.Menu()
        self._set_playlist_actions(app, playlist_menu, object_id, is_album)

        self.insert_section(1, _("Playlists"), playlist_menu)

#######################
# PRIVATE             #
#######################
    """
        Set playback actions
        @param app as Gio.Application
        @param menu as Gio.Menu
        @param object_id as int
    """
    def _set_playback_actions(self, app, menu, object_id):
        if Objects.player.context.next != NextContext.STOP_NONE:
            continue_play_action = Gio.SimpleAction(
                                                name="continue_play_action")
            app.add_action(continue_play_action)
            continue_play_action.connect('activate', self._continue_playback)
            menu.append(_("Continue playback"), 'app.continue_play_action')
        if Objects.player.context.next != NextContext.STOP_TRACK:
            stop_track_action = Gio.SimpleAction(name="stop_track_action")
            app.add_action(stop_track_action)
            stop_track_action.connect('activate', self._stop_track)
            menu.append(_("Stop after this track"), 'app.stop_track_action')
        if Objects.player.context.next != NextContext.STOP_ALBUM:
            stop_album_action = Gio.SimpleAction(name="stop_album_action")
            app.add_action(stop_album_action)
            stop_album_action.connect('activate', self._stop_album)
            menu.append(_("Stop after this album"), 'app.stop_album_action')
        if Objects.player.context.next != NextContext.STOP_ARTIST:
            stop_artist_action = Gio.SimpleAction(name="stop_artist_action")
            app.add_action(stop_artist_action)
            stop_artist_action.connect('activate', self._stop_artist)
            menu.append(_("Stop after this artist"), 'app.stop_artist_action')

    """
        Set playlist actions
        @param app as Gio.Application
        @param menu as Gio.Menu
        @param object_id as int
        @param is album as bool
    """
    def _set_playlist_actions(self, app, menu, object_id, is_album):
        playlist_action = Gio.SimpleAction(name="playlist_action")
        app.add_action(playlist_action)
        playlist_action.connect('activate',
                                self._add_to_playlists,
                                object_id,
                                is_album)
        menu.append(_("Add to others"), 'app.playlist_action')

        i = 0
        for playlist in Objects.playlists.get_last():
            action = Gio.SimpleAction(name="playlist%s" % i)
            app.add_action(action)
            if Objects.playlists.is_present(playlist,
                                            object_id,
                                            self._genre_id,
                                            is_album):
                action.connect('activate',
                               self._del_from_playlist,
                               object_id, is_album,
                               playlist)
                menu.append(_("Remove from \"%s\"") % playlist,
                            "app.playlist%s" % i)
            else:
                action.connect('activate',
                               self._add_to_playlist,
                               object_id,
                               is_album,
                               playlist)
                menu.append(_("Add to \"%s\"") % playlist,
                            "app.playlist%s" % i)
            i += 1

    """
        Set queue actions
        @param app as Gio.Application
        @param menu as Gio.Menu
        @param object_id as int
        @param is album as bool
    """
    def _set_queue_actions(self, app, menu, object_id, is_album):
        queue = Objects.player.get_queue()
        append = True
        prepend = True
        delete = True
        if not queue:
            append = False
        if not is_album:
            if object_id in queue:
                if queue and queue[0] == object_id:
                    prepend = False
                append = False
            else:
                delete = False
        else:

            tracks = Objects.albums.get_tracks(object_id, self._genre_id)
            union = set(queue) & set(tracks)
            if len(union) == len(tracks):
                append = False
                prepend = False
            elif not bool(union):
                delete = False

        append_queue_action = Gio.SimpleAction(name="append_queue_action")
        app.add_action(append_queue_action)
        prepend_queue_action = Gio.SimpleAction(name="prepend_queue_action")
        app.add_action(prepend_queue_action)
        del_queue_action = Gio.SimpleAction(name="del_queue_action")
        app.add_action(del_queue_action)
        if append:
            append_queue_action.connect('activate',
                                        self._append_to_queue,
                                        object_id)
            menu.append(_("Add to queue"), 'app.append_queue_action')
        if prepend:
            prepend_queue_action.connect('activate',
                                         self._prepend_to_queue,
                                         object_id)
            if is_album:
                menu.append(_("Next tracks"), 'app.prepend_queue_action')
            else:
                menu.append(_("Next track"), 'app.prepend_queue_action')
        if delete:
            del_queue_action.connect('activate',
                                     self._del_from_queue,
                                     object_id)
            menu.append(_("Remove from queue"), 'app.del_queue_action')

    """
        Tell player to continue playback
        @param SimpleAction
        @param GVariant
        @param album id as int
    """
    def _continue_playback(self, action, variant):
        Objects.player.current.next = NextContext.STOP_NONE

    """
        Tell player to stop after current track
        @param SimpleAction
        @param GVariant
    """
    def _stop_track(self, action, variant):
        Objects.player.context.next = NextContext.STOP_TRACK

    """
        Tell player to stop after current album
        @param SimpleAction
        @param GVariant
    """
    def _stop_album(self, action, variant):
        Objects.player.context.next = NextContext.STOP_ALBUM

    """
        Tell player to stop after current artist
        @param SimpleAction
        @param GVariant
    """
    def _stop_artist(self, action, variant):
        Objects.player.context.next = NextContext.STOP_ARTIST

    """
        Add to playlists
        @param SimpleAction
        @param GVariant
        @param object id as int
        @param is album as bool
    """
    def _add_to_playlists(self, action, variant, object_id, is_album):
        window = self._parent.get_toplevel()
        window.show_playlist_manager(object_id, is_album)

    """
        Add to playlist
        @param SimpleAction
        @param GVariant
        @param object id as int
        @param is album as bool
        @param playlist name as str
    """
    def _add_to_playlist(self, action, variant, object_id,
                         is_album, playlist_name):
        if is_album:
            tracks_path = Objects.albums.get_tracks_path(object_id,
                                                         self._genre_id)
        else:
            tracks_path = [Objects.tracks.get_path(object_id)]

        start_new_thread(Objects.playlists.add_tracks,
                         (playlist_name, tracks_path))

    """
        Del from playlist
        @param SimpleAction
        @param GVariant
        @param object id as int
        @param is album as bool
        @param playlist name as str
    """
    def _del_from_playlist(self, action, variant, object_id,
                           is_album, playlist_name):
        if is_album:
            tracks_path = Objects.albums.get_tracks_path(object_id,
                                                         self._genre_id)
        else:
            tracks_path = [Objects.tracks.get_path(object_id)]

        start_new_thread(Objects.playlists.remove_tracks,
                         (playlist_name, tracks_path))

    """
        Append track to queue
        @param SimpleAction
        @param GVariant
        @param album id as int
    """
    def _append_to_queue(self, action, variant, album_id):
        if self._is_album:
            for track_id in Objects.albums.get_tracks(album_id,
                                                      self._genre_id):
                Objects.player.append_to_queue(track_id)
        else:
            Objects.player.append_to_queue(album_id)

    """
        Prepend track id to queue
        @param SimpleAction
        @param GVariant
        @param album id as int
    """
    def _prepend_to_queue(self, action, variant, album_id):
        if self._is_album:
            for track_id in reversed(Objects.albums.get_tracks(
                                                    album_id,
                                                    self._genre_id)):
                Objects.player.prepend_to_queue(track_id)
        else:
            Objects.player.prepend_to_queue(album_id)

    """
        Delete track id from queue
        @param SimpleAction
        @param GVariant
        @param album id as int
    """
    def _del_from_queue(self, action, variant, album_id):
        if self._is_album:
            for track_id in Objects.albums.get_tracks(album_id,
                                                      self._genre_id):
                Objects.player.del_from_queue(track_id)
        else:
            Objects.player.del_from_queue(album_id)
