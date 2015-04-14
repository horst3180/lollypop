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
from _thread import start_new_thread
from gettext import gettext as _
import os

from lollypop.define import Objects, Navigation, ArtSize
from lollypop.playlist_widgets import PlaylistsManagerWidget,\
                                      PlaylistEditWidget,\
                                      PlaylistWidget
from lollypop.devicemanager import DeviceManagerWidget
from lollypop.album_widgets import AlbumDetailedWidget, AlbumSimpleWidget
from lollypop.radio_widgets import PopRadio, RadioWidget
from lollypop.utils import translate_artist_name

# Container for a view
class ViewContainer(Gtk.Stack):
    def __init__(self, duration):
        Gtk.Stack.__init__(self)
        self._duration = duration
        # Don't pass resize request to parent
        self.set_resize_mode(Gtk.ResizeMode.QUEUE)
        self.set_transition_duration(duration)
        self.set_transition_type(Gtk.StackTransitionType.CROSSFADE)

    """
        Clean old views
        @param view as new View
    """
    def clean_old_views(self, view):
        for child in self.get_children():
            if child != view:
                child.stop()
                if isinstance(child, DeviceView):
                    self.remove(child)
                else:
                    # Delayed destroy as we may have an animation running
                    # Gtk.StackTransitionType.CROSSFADE
                    GLib.timeout_add(self._duration,
                                     self._delayedclean_view,
                                     child)

#######################
# PRIVATE             #
#######################
    """
        Clean view
        @param valid view as View
    """
    def _delayedclean_view(self, view):
        view.remove_signals()
        view.destroy()


# Generic view
class View(Gtk.Grid):

    def __init__(self):
        Gtk.Grid.__init__(self)
        self.set_property("orientation", Gtk.Orientation.VERTICAL)
        self.set_border_width(0)
        self._current_signal = Objects.player.connect("current-changed",
                                                      self._on_current_changed)
        self._cover_signal = Objects.player.connect("cover-changed",
                                                    self._on_cover_changed)
        # Stop populate thread
        self._stop = False

        self._scrolledWindow = Gtk.ScrolledWindow()
        self._scrolledWindow.set_policy(Gtk.PolicyType.AUTOMATIC,
                                        Gtk.PolicyType.AUTOMATIC)

        self._scrolledWindow.show()
        self._viewport = Gtk.Viewport()
        self._scrolledWindow.add(self._viewport)
        self._viewport.show()

    """
        Remove signals on player object
    """
    def remove_signals(self):
        if self._current_signal:
            Objects.player.disconnect(self._current_signal)
            self._current_signal = None
        if self._cover_signal:
            Objects.player.disconnect(self._cover_signal)
            self._cover_signal = None

    """
        Stop populating
    """
    def stop(self):
        self._stop = True
        for child in self._get_children():
            child.stop()

    """
        Update children's covers
    """
    def update_covers(self):
        GLib.idle_add(self._update_widgets, self._get_children(), True)

#######################
# PRIVATE             #
#######################
    """
        Update all widgets
        @param widgets as AlbumWidget
        @param force as bool
    """
    def _update_widgets(self, widgets, force):
        if len(widgets) > 0:
            widget = widgets.pop(0)
            widget.set_cover(force)
            widget.update_playing_indicator()
            GLib.idle_add(self._update_widgets, widgets, force)

    """
        Return view children
    """
    def _get_children(self):
        return []

    """
        Update album cover in view
        @param player as Player
        @param album id as int, if None, use object name
        @param object name as str, unused if album id not None
    """
    def _on_cover_changed(self, player, album_id, object_name):
        if album_id is not None:
            param = album_id
        else:
            param = object_name

        for widget in self._get_children():
            widget.update_cover(param)

    """
        Current song changed
        @param player as Player
    """
    def _on_current_changed(self, player):
        GLib.idle_add(self._update_widgets, self._get_children(), False)


# Artist view is a vertical grid with album songs widgets
class ArtistView(View):
    """
        Init ArtistView ui with a scrolled grid of AlbumDetailedWidget
        @param artist id as int
        @param show_artist_details as bool
    """
    def __init__(self, artist_id, show_artist_details):
        View.__init__(self)
        self._artist_id = artist_id
        self._signal_id = None

        if show_artist_details:
            builder = Gtk.Builder()
            builder.add_from_resource('/org/gnome/Lollypop/ArtistView.ui')
            self.attach(builder.get_object('ArtistView'),0, 0, 1, 1)
            artist_name = Objects.artists.get_name(artist_id)
            artist_name = translate_artist_name(artist_name)
            builder.get_object('artist').set_label(artist_name)

        self._show_menu = show_artist_details

        self._albumbox = Gtk.Grid()
        self._albumbox.set_row_spacing(20)
        self._albumbox.set_property("orientation", Gtk.Orientation.VERTICAL)
        self._albumbox.show()

        self._scrolledWindow.set_property('expand', True)
        self._viewport.set_property("valign", Gtk.Align.START)
        self._viewport.add(self._albumbox)
        self.add(self._scrolledWindow)

    """
        Populate the view, can be threaded
        @param navigation id as int
    """
    def populate(self, navigation_id):
        sql = Objects.db.get_cursor()
        if self._artist_id == Navigation.COMPILATIONS:
            albums = Objects.albums.get_compilations(navigation_id,
                                                     sql)
        elif navigation_id == Navigation.ALL:
            albums = Objects.albums.get_ids(self._artist_id,
                                            None,
                                            sql)
        else:
            albums = Objects.albums.get_ids(self._artist_id,
                                            navigation_id,
                                            sql)
        GLib.idle_add(self._add_albums, albums, navigation_id)
        sql.close()

#######################
# PRIVATE             #
#######################
    """
        Return view children
        @return [AlbumWidget]
    """
    def _get_children(self):
        return self._albumbox.get_children()

    """
        Pop an album and add it to the view,
        repeat operation until album list is empty
        @param [album ids as int]
        @param genre id as int
    """
    def _add_albums(self, albums, genre_id):
        size_group = Gtk.SizeGroup(mode=Gtk.SizeGroupMode.HORIZONTAL)
        if len(albums) > 0 and not self._stop:
            widget = AlbumDetailedWidget(albums.pop(0),
                                         genre_id,
                                         self._show_menu,
                                         size_group)
            widget.show()
            start_new_thread(widget.populate, ())
            self._albumbox.add(widget)
            GLib.idle_add(self._add_albums, albums, genre_id)
        else:
            self._stop = False


# Album contextual view
class AlbumContextView(View):
    """
        Init context
        @param main view widget
    """
    def __init__(self, widget):
        View.__init__(self)
        self._widget = widget
        self._viewport.add(widget)
        self._viewport.show()
        self._scrolledWindow.set_min_content_height(ArtSize.BIG+25)
        self._scrolledWindow.show()
        self.add(self._scrolledWindow)

#######################
# PRIVATE             #
#######################
    """
        Return view children
        @return [AlbumWidget]
    """
    def _get_children(self):
        return [self._widget]


# Album view is a flowbox of albums widgets with album name and artist name
class AlbumView(View):
    """
        Init album view ui with a scrolled flow box and a scrolled context view
        @param navigation id as int
    """
    def __init__(self, navigation_id):
        View.__init__(self)
        self._signal = None
        self._context_album_id = None
        self._genre_id = navigation_id
        self._albumsongs = None
        self._context_widget = None

        self._albumbox = Gtk.FlowBox()
        self._albumbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self._albumbox.connect("child-activated", self._on_album_activated)
        self._albumbox.set_max_children_per_line(100)
        self._albumbox.show()

        self._viewport.set_property("valign", Gtk.Align.START)
        self._viewport.add(self._albumbox)
        self._scrolledWindow.set_property('expand', True)

        self._context = ViewContainer(500)

        separator = Gtk.Separator()
        separator.show()

        paned = Gtk.Paned.new(Gtk.Orientation.VERTICAL)
        paned.pack1(self._scrolledWindow)
        paned.pack2(self._context, True, False)
        height = Objects.settings.get_value(
                                         'paned-context-height').get_int32()
        # We set a stupid max value, safe as self._context is shrinked
        if height == -1:
            height = 10000000
        paned.set_position(height)
        paned.connect('notify::position', self._on_position_notify)
        paned.show()
        self.add(paned)

    """
        Populate albums, thread safe
        @param navigation id as int
    """
    def populate(self, navigation_id):
        sql = Objects.db.get_cursor()
        if self._genre_id == Navigation.ALL:
            albums = Objects.albums.get_ids(None, None, sql)
        elif self._genre_id == Navigation.POPULARS:
            albums = Objects.albums.get_populars(sql)
        elif self._genre_id == Navigation.COMPILATIONS:
            albums = Objects.albums.get_compilations(navigation_id,
                                                     sql)
        else:
            albums = Objects.albums.get_ids(None, self._genre_id, sql)
        GLib.idle_add(self._add_albums, albums)
        sql.close()

#######################
# PRIVATE             #
#######################
    """
        Return view children
        @return [AlbumWidget]
    """
    def _get_children(self):
        children = []
        for child in self._albumbox.get_children():
            for widget in child.get_children():
                children.append(widget)
        return children

    """
        populate context view
        @param album id as int
    """
    def _populate_context(self, album_id):
        size_group = Gtk.SizeGroup(mode=Gtk.SizeGroupMode.HORIZONTAL)
        self._context_widget = AlbumDetailedWidget(album_id,
                                                   self._genre_id,
                                                   True,
                                                   size_group)
        start_new_thread(self._context_widget.populate, ())
        self._context_widget.show()
        view = AlbumContextView(self._context_widget)
        view.show()
        self._context.add(view)
        self._context.set_visible_child(view)
        self._context.clean_old_views(view)

    """
        Save paned position
        @param paned as Gtk.Paned
        @param param as Gtk.Param
    """
    def _on_position_notify(self, paned, param):
        Objects.settings.set_value(
                            'paned-context-height',
                            GLib.Variant('i', paned.get_position()))
        return False

    """
        Show Context view for activated album
        @param flowbox, children
    """
    def _on_album_activated(self, flowbox, child):
        if self._context_album_id == child.get_child().get_id():
            if Objects.settings.get_value('auto-play'):
                Objects.player.play_album(self._context_album_id)
            else:
                self._context_album_id = None
                self._context.hide()
        else:
            self._context_album_id = child.get_child().get_id()
            self._populate_context(self._context_album_id)
            self._context.show()

    """
        Pop an album and add it to the view,
        repeat operation until album list is empty
        @param [album ids as int]
    """
    def _add_albums(self, albums):
        if len(albums) > 0 and not self._stop:
            widget = AlbumSimpleWidget(albums.pop(0))
            widget.show()
            self._albumbox.insert(widget, -1)
            GLib.idle_add(self._add_albums, albums)
        else:
            self._stop = False


# Playlist view is a vertical grid with album's covers
class PlaylistView(View):
    """
        Init PlaylistView ui with a scrolled grid of PlaylistWidgets
        @param playlist name as str
    """
    def __init__(self, playlist_name, parent):
        View.__init__(self)
        self._playlist_name = playlist_name
        self._signal_id = None

        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/PlaylistView.ui')
        builder.get_object('title').set_label(playlist_name)
        builder.connect_signals(self)

        self._edit_btn = builder.get_object('edit_btn')
        self._back_btn = builder.get_object('back_btn')
        self._title = builder.get_object('title')

        self._playlist_widget = PlaylistWidget(playlist_name)
        self._playlist_widget.show()

        self.add(builder.get_object('PlaylistView'))
        self._viewport.add(self._playlist_widget)
        self._scrolledWindow.set_property('expand', True)
        self.add(self._scrolledWindow)

    """
        Populate view with tracks from playlist
        Thread safe
    """
    def populate(self):
        sql = Objects.db.get_cursor()
        tracks = Objects.playlists.get_tracks_id(self._playlist_name, sql)
        mid_tracks = int(0.5+len(tracks)/2)
        self._playlist_widget.populate_list_one(tracks[:mid_tracks],
                                                1)
        self._playlist_widget.populate_list_two(tracks[mid_tracks:],
                                                mid_tracks + 1)

    """
        Return playlist name
        @return name as str
    """
    def get_name(self):
        return self._playlist_name

    """
        Do show, connect signals
    """
    def do_show(self):
        self._signal_id = Objects.playlists.connect("playlist-changed",
                                                    self._update_view)
        View.do_show(self)

    """
        Do hide, disconnect signals
    """
    def do_hide(self):
        if self._signal_id:
            Objects.playlists.disconnect(self._signal_id)
            self._signal_id = None
        View.do_hide(self)

#######################
# PRIVATE             #
#######################
    """
        Update tracks widgets
        @param manager as PlaylistsManager
        @param playlist name as str
    """
    def _update_view(self, manager, playlist_name):
        if playlist_name == self._playlist_name:
            self._playlist_widget.clear()
            start_new_thread(self.populate, ())

    """
        Edit playlist
        @param button as Gtk.Button
        @param playlist name as str
    """
    def _on_edit_btn_clicked(self, button):
        Objects.window.show_playlist_editor(self._playlist_name)

    """
        Current song changed
        @param player as Player
    """
    def _on_current_changed(self, player):
        self._playlist_widget.update_playing_indicator()


# Playlist view used to manage playlists
class PlaylistManageView(View):
    """
         @param object id as int
         @param genre id as int
         @param is album as bool
         @param width as int
    """
    def __init__(self, object_id, genre_id, is_album, width):
        View.__init__(self)
        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/PlaylistsManagerView.ui')
        if object_id != -1:
            builder.get_object('back_btn').show()
        builder.connect_signals(self)
        self._manage_widget = PlaylistsManagerWidget(object_id,
                                                     genre_id,
                                                     is_album)
        self._manage_widget.show()
        self._scrolledWindow.set_property('halign', Gtk.Align.CENTER)
        self._scrolledWindow.set_property('width-request', width)
        self._viewport.add(self._manage_widget)
        self.add(builder.get_object('widget'))
        self.add(self._scrolledWindow)

    def populate(self):
        self._manage_widget.populate()

#######################
# PRIVATE             #
#######################
    """
        Add new playlist
        @param widget as Gtk.Button
    """
    def _on_new_clicked(self, widget):
        self._manage_widget.add_new_playlist()

    """
        Restore previous view
        @param button as Gtk.Button
    """
    def _on_back_btn_clicked(self, button):
        Objects.window.destroy_current_view()

# Playlist view used to edit playlists
class PlaylistEditView(View):
    """
         @param playlist name as str
         @param width as int
    """
    def __init__(self, playlist_name, width):
        View.__init__(self)
        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/PlaylistEditView.ui')
        builder.get_object('title').set_label(playlist_name)
        builder.connect_signals(self)
        grid = builder.get_object('widget')
        self.add(grid)
        self._edit_widget = PlaylistEditWidget(playlist_name)
        self._edit_widget.show()
        self._scrolledWindow.set_property('halign', Gtk.Align.CENTER)
        self._scrolledWindow.set_property('width-request', width)
        self._viewport.add(self._edit_widget)
        self.add(self._scrolledWindow)

    def populate(self):
        self._edit_widget.populate()

#######################
# PRIVATE             #
#######################
    """
        Restore previous view
        @param button as Gtk.Button
    """
    def _on_back_btn_clicked(self, button):
        Objects.window.destroy_current_view()


# Radio view
class RadiosView(View):
    def __init__(self):
        View.__init__(self)
        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/RadioView.ui')
        builder.connect_signals(self)
        self._viewport.add(builder.get_object('widget'))
        self.add(self._scrolledWindow)

    def populate(self):
        pass

#######################
# PRIVATE             #
#######################
    """
        Show popover for playlist creation
        @param widget as Gtk.Widget
    """
    def _on_new_clicked(self, widget):
        popover = PopRadio()
        popover.set_relative_to(widget)
        popover.show()


# Playlist synchronisation view
class DeviceView(View):
    """
        @param device as Device
        @param progress as Gtk.ProgressBar
        @param width as int
    """
    def __init__(self, device, progress, width):
        View.__init__(self)
        self._device = device
        self._progress = progress
        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/DeviceManagerView.ui')
        self._memory_combo = builder.get_object('memory_combo')
        self._syncing_btn = builder.get_object('sync_btn')
        self._syncing_btn.set_label(_("Synchronize %s") % device.name)
        builder.connect_signals(self)
        grid = builder.get_object('widget')
        self.add(grid)
        self._device_widget = DeviceManagerWidget(device, progress, self)
        self._device_widget.connect('sync-finished', self._on_sync_finished)
        self._device_widget.show()
        self._scrolledWindow.set_property('halign', Gtk.Align.CENTER)
        self._scrolledWindow.set_property('width-request', width)
        self._viewport.add(self._device_widget)
        self.add(self._scrolledWindow)

    def populate(self):
        files = os.listdir(self._device.path)
        GLib.idle_add(self._set_combo_text, files)

    def is_syncing(self):
        return self._device_widget.is_syncing()

#######################
# PRIVATE             #
#######################
    """
        Start synchronisation
        @param widget as Gtk.Button
    """
    def _on_sync_clicked(self, widget):
        if self._device_widget.is_syncing():
            self._device_widget.cancel_sync()
            self._on_sync_finished(None)
        elif not self._progress.is_visible():
            self._memory_combo.hide()
            self._syncing_btn.set_label(_("Cancel synchronization"))
            self._device_widget.sync()

    """
        Restore widgets state
        @param device widget as DeviceManager
    """
    def _on_sync_finished(self, device_widget):
        self._memory_combo.show()
        self._syncing_btn.set_label(_("Synchronize %s") %
                                    self._device.name)
    """
        Update path
        @param combo as Gtk.ComboxText
    """
    def _on_memory_combo_changed(self, combo):
        text = combo.get_active_text()
        path = "%s/%s/Music/%s" % (self._device.path, text, "lollypop")
        try:
            if not os.path.exists(path+"/tracks"):
                self._mkdir(path+"/tracks")
            on_disk_playlists = os.listdir(path)
        except Exception as e:
            print("DeviceManagerWidget::_on_memory_combo_changed: %s" % e)
            on_disk_playlists = []
        self._device_widget.set_playlists(on_disk_playlists, path)
        start_new_thread(self._device_widget.populate, ())

    """
        Set combobox text
        @param text list as [str]
    """
    def _set_combo_text(self, text_list):
        for text in text_list:
            self._memory_combo.append_text(text)
        self._memory_combo.set_active(0)


