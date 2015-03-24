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

from gi.repository import Gtk, GLib
from cgi import escape

from lollypop.define import Objects, Navigation, ArtSize
from lollypop.tracks import TracksWidget
from lollypop.popmenu import PopMainMenu
from lollypop.playlists import PlaylistEditWidget
from lollypop.popimages import PopImages
from lollypop.utils import translate_artist_name


# Album widget is a pixbuf with two labels: albumm name and artist name
class AlbumWidget(Gtk.Grid):

    """
        Init album widget ui with an vertical grid:
            - Album cover
            - Album name
            - Artist name
    """
    def __init__(self, album_id):
        Gtk.Grid.__init__(self)
        self._album_id = album_id

        self.set_property("margin", 5)

        self.set_orientation(Gtk.Orientation.VERTICAL)
        self._ui = Gtk.Builder()
        self._ui.add_from_resource('/org/gnome/Lollypop/AlbumWidget.ui')

        self._cover = self._ui.get_object('cover')
        self._cover.set_from_pixbuf(Objects.art.get(album_id, ArtSize.BIG))

        album_name = Objects.albums.get_name(album_id)
        title = self._ui.get_object('title')
        title.set_label(album_name)
        artist_name = Objects.albums.get_artist_name(album_id)
        artist_name = translate_artist_name(artist_name)
        artist = self._ui.get_object('artist')
        artist.set_label(artist_name)

        self.add(self._cover)
        self.add(title)
        self.add(artist)

    def do_get_preferred_width(self):
        return (ArtSize.BIG, ArtSize.BIG)

    """
        Update cover for album id
        @param album id as int
    """
    def update_cover(self, album_id):
        if self._album_id == album_id:
            self._cover.set_from_pixbuf(Objects.art.get(album_id,
                                                        ArtSize.BIG))

    """
        Return album id for widget
        @return album id as int
    """
    def get_id(self):
        return self._album_id


# Album detailed Widget is a pixbuf with album name and tracks list
class AlbumDetailedWidget(Gtk.Grid):
    """
        Init album widget songs ui with a complex grid:
            - Album cover
            - Album name
            - Albums tracks aligned on two columns
        if cover_add True, let user change album cover
        @param album id as int
        @param genre id as int
        @param parent width as int
        @param limit_to_artist as bool to load artist albums on play
        @param show_menu as bool if menu need to be displayed
        @param size group as Gtk.SizeGroup
    """
    def __init__(self, album_id, genre_id, limit_to_artist,
                 show_menu, size_group):
        Gtk.Grid.__init__(self)
        self._stop = False

        self._ui = Gtk.Builder()
        self._ui.add_from_resource(
                    '/org/gnome/Lollypop/AlbumDetailedWidget.ui')

        self._artist_id = Objects.albums.get_artist_id(album_id)
        self._album_id = album_id
        self._genre_id = genre_id
        self._limit_to_artist = limit_to_artist

        self._tracks_widget1 = TracksWidget(show_menu)
        self._tracks_widget2 = TracksWidget(show_menu)
        size_group.add_widget(self._tracks_widget1)
        size_group.add_widget(self._tracks_widget2)
        self._tracks_widget1.connect('activated', self._on_activated)
        self._tracks_widget2.connect('activated', self._on_activated)
        self._ui.get_object('tracks').add(self._tracks_widget1)
        self._ui.get_object('tracks').add(self._tracks_widget2)
        self._tracks_widget1.show()
        self._tracks_widget2.show()

        self._cover = self._ui.get_object('cover')
        self._cover.set_from_pixbuf(Objects.art.get(album_id, ArtSize.BIG))
        self._ui.get_object('title').set_label(
                                            Objects.albums.get_name(album_id))
        self._ui.get_object('year').set_label(
                                            Objects.albums.get_year(album_id))
        self.add(self._ui.get_object('AlbumDetailedWidget'))

        if show_menu:
            self.eventbox = self._ui.get_object('eventbox')
            self.eventbox.connect("button-press-event",
                                  self._show_web_art)
            self._ui.get_object('menu').connect('clicked',
                                                self._pop_menu)
            self._ui.get_object('menu').show()
        else:
            self.eventbox = None

    """
        Update playing track
        @param track id as int
    """
    def update_playing_track(self, track_id):
        self._tracks_widget1.update_playing(track_id)
        self._tracks_widget2.update_playing(track_id)

    """
        Update cover for album id
        @param album id as int
    """
    def update_cover(self, album_id):
        if self._album_id == album_id:
            self._cover.set_from_pixbuf(Objects.art.get(album_id,
                                                        ArtSize.BIG))

    """
        Return album id for widget
        @return album id as int
    """
    def get_id(self):
        return self._album_id

    """
        Populate tracks
    """
    def populate(self):
        self._stop = False
        sql = Objects.db.get_cursor()
        mid_tracks = int(0.5+Objects.albums.get_count(self._album_id,
                                                      self._genre_id,
                                                      sql)/2)
        tracks = Objects.albums.get_tracks_infos(self._album_id,
                                                 self._genre_id,
                                                 sql)
        self.populate_list_one(tracks[:mid_tracks],
                               1)
        self.populate_list_two(tracks[mid_tracks:],
                               mid_tracks + 1)

    """
        Populate list one, thread safe
        @param track's ids as array of int
        @param track position as int
    """
    def populate_list_one(self, tracks, pos):
        GLib.idle_add(self._add_tracks,
                      tracks,
                      self._tracks_widget1,
                      pos)

    """
        Populate list two, thread safe
        @param track's ids as array of int
        @param track position as int
    """
    def populate_list_two(self, tracks, pos):
        GLib.idle_add(self._add_tracks,
                      tracks,
                      self._tracks_widget2,
                      pos)

    """
        Stop populating
    """
    def stop(self):
        self._stop = True
#######################
# PRIVATE             #
#######################
    """
        Popup menu for album
        @param widget as Gtk.Button
        @param album id as int
    """
    def _pop_menu(self, widget):
        menu = PopMainMenu(self._album_id, self._genre_id, True, False, widget)
        popover = Gtk.Popover.new_from_model(self._ui.get_object('menu'), menu)
        popover.show()

    """
        Add tracks for to Album widget
        @param tracks as [(track_id, title, length, [artist ids])]
        @param widget as TracksWidget
        @param i as int
    """
    def _add_tracks(self, tracks, widget, i):
        if not tracks or self._stop:
            self._stop = False
            return
        track = tracks.pop(0)
        track_id = track[0]
        title = escape(track[1])
        length = track[2]
        artist_ids = track[3]

        # If we are listening to a compilation, prepend artist name
        if self._artist_id == Navigation.COMPILATIONS or\
           len(artist_ids) > 1 or\
           self._artist_id not in artist_ids:
            artist_name = ""
            for artist_id in artist_ids:
                artist_name += translate_artist_name(
                                Objects.artists.get_name(artist_id)) + ", "
            title = "<b>%s</b>\n%s" % (escape(artist_name[:-2]),
                                       title)

        # Get track position in queue
        pos = None
        if Objects.player.is_in_queue(track_id):
            pos = Objects.player.get_track_position(track_id)

        widget.add_track(track_id,
                         i,
                         title,
                         length,
                         pos)
        GLib.idle_add(self._add_tracks, tracks, widget, i+1)

    """
        On track activation, play track
        @param widget as TracksWidget
        @param track id as int
    """
    def _on_activated(self, widget, track_id):
        if not Objects.player.is_party():
            Objects.player.set_albums(track_id,
                                      self._album_id,
                                      self._artist_id,
                                      self._genre_id,
                                      self._limit_to_artist)
        Objects.player.load(track_id)

    """
        Popover with album art downloaded from the web (in fact google :-/)
        @param: widget as eventbox
        @param: data as unused
    """
    def _show_web_art(self, widget, data):
        artist = Objects.artists.get_name(self._artist_id)
        album = Objects.albums.get_name(self._album_id)
        popover = PopImages(self._album_id)
        popover.set_relative_to(widget)
        popover.populate(artist + " " + album)
        popover.show()


# Playlist Widget is similar to album detailed
# widget but show a cover grid as playlist cove
class PlaylistWidget(Gtk.Grid):
    """
        Init playlist Widget
        @param playlist name as str
        @param infobar as Gtk.InfoBar
        @param label as Gtk.Label
    """
    def __init__(self, playlist_name, infobar, infobar_label):
        Gtk.Grid.__init__(self)
        self._tracks = []
        self.set_property("margin", 5)

        self._ui = Gtk.Builder()
        self._ui.add_from_resource(
                '/org/gnome/Lollypop/PlaylistWidget.ui'
                                  )

        self._tracks_widget1 = TracksWidget(False)
        self._tracks_widget2 = TracksWidget(False)
        self._tracks_widget1.connect('activated',
                                     self._on_activated, playlist_name)
        self._tracks_widget2.connect('activated',
                                     self._on_activated, playlist_name)
        self._tracks_widget1.show()
        self._tracks_widget2.show()

        size_group = Gtk.SizeGroup(mode=Gtk.SizeGroupMode.HORIZONTAL)
        size_group.add_widget(self._tracks_widget1)
        size_group.add_widget(self._tracks_widget2)

        self._playlist_widget = self._ui.get_object('scroll')
        self._ui.get_object('grid').add(self._tracks_widget1)
        self._ui.get_object('grid').add(self._tracks_widget2)

        self._stack = Gtk.Stack()
        self._playlist_edit = PlaylistEditWidget(playlist_name,
                                                 infobar,
                                                 infobar_label,
                                                 self)
        self._stack.add(self._playlist_edit.widget)
        self._stack.add(self._playlist_widget)
        self._stack.set_visible_child(self._playlist_widget)
        self._stack.set_transition_duration(500)
        self._stack.set_property('expand', True)
        self._stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self._stack.show()

        self.add(self._stack)

    """
        Populate list one, thread safe
        @param track's ids as array of int
        @param track position as int
    """
    def populate_list_one(self, tracks, pos):
        GLib.idle_add(self._add_tracks,
                      tracks,
                      self._tracks_widget1,
                      pos)

    """
        Populate list two, thread safe
        @param track's ids as array of int
        @param track position as int
    """
    def populate_list_two(self, tracks, pos):
        GLib.idle_add(self._add_tracks,
                      tracks,
                      self._tracks_widget2,
                      pos)

    """
        Update playing track
        @param track id as int
    """
    def update_playing_track(self, track_id):
        self._tracks_widget1.update_playing(track_id)
        self._tracks_widget2.update_playing(track_id)

    """
        Popup menu for playlist
        @param edit as bool
    """
    def edit(self, edit):
        if edit:
            self._stack.set_visible_child(self._playlist_edit.widget)
            self._playlist_edit.populate()
        else:
            self._stack.set_visible_child(self._playlist_widget)
            self._playlist_edit.unselectall()

    """
        Unselect all in edit widget
    """
    def unselectall(self):
        self._playlist_edit.unselectall()

    """
        Delete playlist after confirmation
    """
    def delete_confirmed(self):
        self._playlist_edit.delete_confirmed()

    """
        Clear tracks
    """
    def clear(self):
        self._tracks = []
        for child in self._tracks_widget1.get_children():
            child.destroy()
        for child in self._tracks_widget2.get_children():
            child.destroy()

#######################
# PRIVATE             #
#######################
    """
        Add tracks to list
        @param tracks id as array of [int]
        @param widget TracksWidget
        @param track position as int
    """
    def _add_tracks(self, tracks, widget, pos):
        if not tracks:
            return

        track_id = tracks.pop(0)
        if track_id == -1:
            return

        (title, filepath, length, album_id) =\
            Objects.tracks.get_infos(track_id)

        artist_name = ""
        for artist_id in Objects.tracks.get_artist_ids(track_id):
            artist_name += translate_artist_name(
                            Objects.artists.get_name(artist_id)) + ", "
        title = "<b>%s</b>\n%s" % (escape(artist_name[:-2]),
                                   escape(title))

        widget.add_track(track_id, pos, title, length, None, True)
        GLib.idle_add(self._add_tracks, tracks, widget, pos+1)

    """
        On track activation, play track
        @param widget as TracksWidget
        @param track id as int
        @param playlist name as str
    """
    def _on_activated(self, widget, track_id, playlist_name):
        if not Objects.player.is_party():
            if not self._tracks:
                self._tracks = Objects.playlists.get_tracks_id(playlist_name)
            Objects.player.set_user_playlist(self._tracks, track_id)
        Objects.player.load(track_id)
