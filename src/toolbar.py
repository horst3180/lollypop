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
from gi.repository import Gtk, Gdk, GLib, Gio
from cgi import escape

from lollypop.define import Objects, Shuffle, ArtSize
from lollypop.search import SearchWidget
from lollypop.popmenu import PopMainMenu
from lollypop.queue import QueueWidget
from lollypop.utils import seconds_to_string
from lollypop.popalbums import PopAlbums


# Toolbar as headerbar
# Get real widget with Toolbar.widget
class Toolbar:
    """
        Init toolbar/headerbar ui
        @param app as Gtk.Application
    """
    def __init__(self, app):
        # Prevent updating progress while seeking
        self._seeking = False
        # Update pogress position
        self._timeout = None

        self._ui = Gtk.Builder()
        self._ui.add_from_resource('/org/gnome/Lollypop/headerbar.ui')
        self.header_bar = self._ui.get_object('header-bar')
        self.header_bar.set_custom_title(self._ui.get_object('title-box'))

        self._prev_btn = self._ui.get_object('previous_button')
        self._play_btn = self._ui.get_object('play_button')
        self._next_btn = self._ui.get_object('next_button')
        self._play_image = self._ui.get_object('play_image')
        self._pause_image = self._ui.get_object('pause_image')

        self._progress = self._ui.get_object('progress_scale')
        self._progress.set_sensitive(False)
        self._progress.connect('button-release-event',
                               self._on_progress_release_button)
        self._progress.connect('button-press-event',
                               self._on_progress_press_button)

        self._timelabel = self._ui.get_object('playback')
        self._total_time_label = self._ui.get_object('duration')

        self._title_label = self._ui.get_object('title')
        self._artist_label = self._ui.get_object('artist')
        self._cover = self._ui.get_object('cover')
        self._infobox = self._ui.get_object('infobox')
        self._infobox.connect("button-press-event", self._pop_infobox)
        self._popalbums = PopAlbums()
        self._popalbums.set_relative_to(self._infobox)

        Objects.player.connect("status-changed", self._on_status_changed)
        Objects.player.connect("current-changed", self._on_current_changed)
        Objects.player.connect("cover-changed", self._update_cover)

        self._shuffle_btn = self._ui.get_object('shuffle-button')
        self._shuffle_btn_image = self._ui.get_object('shuffle-button-image')
        self._set_shuffle_icon()
        Objects.settings.connect('changed::shuffle', self._shuffle_btn_aspect)

        self._party_btn = self._ui.get_object('party-button')
        self._party_btn.connect("toggled", self._on_party_btn_toggled)
        partyAction = Gio.SimpleAction.new('party', None)
        partyAction.connect('activate', self._activate_party_button)
        app.add_action(partyAction)
        app.add_accelerator("<Control>p", "app.party")

        self._prev_btn.connect('clicked', self._on_prev_btn_clicked)
        self._play_btn.connect('clicked', self._on_play_btn_clicked)
        self._next_btn.connect('clicked', self._on_next_btn_clicked)

        self._view_genres_btn = self._ui.get_object('genres_button')
        self._view_genres_btn.set_active(
                                not Objects.settings.get_value('hide-genres'))
        self._view_genres_btn.connect("toggled", self._save_genres_btn_state)

        search_button = self._ui.get_object('search-button')
        search_button.connect("clicked", self._on_search_btn_clicked)
        self._search = SearchWidget(self.header_bar)
        self._search.set_relative_to(search_button)
        searchAction = Gio.SimpleAction.new('search', None)
        searchAction.connect('activate', self._on_search_btn_clicked)
        app.add_action(searchAction)
        app.add_accelerator("<Control>f", "app.search")

        queue_button = self._ui.get_object('queue-button')
        queue_button.connect("clicked", self._on_queue_btn_clicked)
        self._queue = QueueWidget()
        self._queue.set_relative_to(queue_button)

        self._settings_button = self._ui.get_object('settings-button')

    """
        @return view genres button as GtkToggleButton
    """
    def get_view_genres_btn(self):
        return self._view_genres_btn

    """
        Add an application menu to menu button
        @parma: menu as Gio.Menu
    """
    def setup_menu_btn(self, menu):
        self._settings_button.show()
        self._settings_button.set_menu_model(menu)

#######################
# PRIVATE             #
#######################

    """
        Set shuffle icon
    """
    def _set_shuffle_icon(self):
        shuffle = Objects.settings.get_enum('shuffle')
        if shuffle == Shuffle.NONE:
            self._shuffle_btn_image.set_from_icon_name(
                                    "media-playlist-consecutive-symbolic",
                                    Gtk.IconSize.SMALL_TOOLBAR)
        else:
            self._shuffle_btn_image.set_from_icon_name(
                                    "media-playlist-shuffle-symbolic",
                                    Gtk.IconSize.SMALL_TOOLBAR)

    """
        Mark shuffle button as active when shuffle active
        @param settings as Gio.Settings, value as str
    """
    def _shuffle_btn_aspect(self, settings, value):
        self._set_shuffle_icon()

    """
        Save button state
        @param widget as GtkToggleButton
    """
    def _save_genres_btn_state(self, widget):
        Objects.settings.set_value('hide-genres',
                                   GLib.Variant('b',
                                                not widget.get_active()))

    """
        Pop albums from current artistleft click
        Show playlist menu on right
        @param widget as Gtk.EventBox
        @param event as Gtk.Event
    """
    def _pop_infobox(self, widget, event):
        if Objects.player.current.id:
            if event.button == 1:
                self._popalbums.populate()
                self._popalbums.show()
            else:
                menu = PopMainMenu(Objects.player.current.id,
                                   False, True, widget)
                popover = Gtk.Popover.new_from_model(self._infobox, menu)
                popover.show()
            return True

    """
        Update cover for album_id
        @param obj as unused, album id as int
    """
    def _update_cover(self, obj, album_id):
        if Objects.player.current.album_id == album_id:
            self._cover.set_from_pixbuf(Objects.art.get(album_id,
                                                        ArtSize.SMALL))

    """
        On press, mark player as seeking
        @param unused
    """
    def _on_progress_press_button(self, scale, data):
        self._seeking = True

    """
        Callback for scale release button
        Seek player to scale value
        @param scale as Gtk.Scale, data as unused
    """
    def _on_progress_release_button(self, scale, data):
        value = scale.get_value()
        self._seeking = False
        self._update_position(value)
        Objects.player.seek(value/60)

    """
        Update toolbar items with track_id informations:
            - Cover
            - artist/title
            - reset progress bar
            - update time/total labels
        @param player as Player
    """
    def _on_current_changed(self, player):
        if player.current.id is None:
            self._infobox.get_window().set_cursor(
                                        Gdk.Cursor(Gdk.CursorType.LEFT_PTR))
            self._cover.hide()
            self._timelabel.hide()
            self._total_time_label.hide()
            self._prev_btn.set_sensitive(False)
            self._progress.set_sensitive(False)
            self._play_btn.set_sensitive(False)
            self._next_btn.set_sensitive(False)
            self._title_label.hide()
            self._artist_label.hide()
        else:
            self._infobox.get_window().set_cursor(
                                        Gdk.Cursor(Gdk.CursorType.HAND1))
            art = Objects.art.get(player.current.album_id,  ArtSize.SMALL)
            if art:
                self._cover.set_from_pixbuf(art)
                self._cover.show()
            else:
                self._cover.hide()

            self._title_label.show()
            self._title_label.set_markup("<span font_desc='Sans 10.5'>"
                                         "%s</span>" %
                                         escape(player.current.title))
            self._artist_label.show()
            self._artist_label.set_markup("<span font_desc='Sans 10.5'>"
                                          "%s</span>" %
                                          escape(player.current.artist))
            self._progress.set_value(0.0)
            self._progress.set_range(0.0, player.current.duration * 60)
            self._total_time_label.set_text(
                                    seconds_to_string(player.current.duration))
            self._total_time_label.show()
            self._timelabel.set_text("0:00")
            self._timelabel.show()

    """
        Update buttons and progress bar
        @param progress as Gtk.Range
    """
    def _on_status_changed(self, progress):
        is_playing = Objects.player.is_playing()
        self._progress.set_sensitive(is_playing)
        if is_playing and not self._timeout:
            self._timeout = GLib.timeout_add(1000, self._update_position)
            self._change_play_btn_status(self._pause_image, _("Pause"))
            self._prev_btn.set_sensitive(True)
            self._play_btn.set_sensitive(True)
            self._next_btn.set_sensitive(True)
            # Party mode can be activated
            # in fullscreen mode, so check button state
            self._party_btn.set_active(Objects.player.is_party())
        elif not is_playing and self._timeout:
            GLib.source_remove(self._timeout)
            self._timeout = None
            self._change_play_btn_status(self._play_image, _("Play"))

    """
        Previous track on prev button clicked
        @param button as Gtk.Button
    """
    def _on_prev_btn_clicked(self, button):
        Objects.player.prev()

    """
        Play/Pause on play button clicked
        @param button as Gtk.Button
    """
    def _on_play_btn_clicked(self, button):
        if Objects.player.is_playing():
            Objects.player.pause()
            self._change_play_btn_status(self._play_image, _("Play"))
        else:
            Objects.player.play()
            self._change_play_btn_status(self._pause_image, _("Pause"))

    """
        Next track on next button clicked
        @param button as Gtk.Button
    """
    def _on_next_btn_clicked(self, button):
        Objects.player.next()

    """
        Show search widget on search button clicked
        @param obj as Gtk.Button or Gtk.Action
    """
    def _on_search_btn_clicked(self, obj, param=None):
        self._search.show()

    """
        Show queue widget on queue button clicked
        @param button as Gtk.Button
    """
    def _on_queue_btn_clicked(self, button):
        self._queue.show()

    """
        Update play button with image and status as tooltip
        @param image as Gtk.Image
        @param status as str
    """
    def _change_play_btn_status(self, image, status):
        self._play_btn.set_image(image)
        self._play_btn.set_tooltip_text(status)

    """
        Activate party button
    """
    def _activate_party_button(self, action, param):
        self._party_btn.set_active(not self._party_btn.get_active())

    """
        Set party mode on if party button active
        @param obj as Gtk.button
    """
    def _on_party_btn_toggled(self, button):
        active = self._party_btn.get_active()
        self._shuffle_btn.set_sensitive(not active)
        if not Objects.settings.get_value('dark-ui'):
            settings = Gtk.Settings.get_default()
            settings.set_property("gtk-application-prefer-dark-theme", active)
        Objects.player.set_party(active)

    """
        Update progress bar position
        @param value as int
    """
    def _update_position(self, value=None):
        if not self._seeking:
            if value is None:
                value = Objects.player.get_position_in_track()/1000000
            self._progress.set_value(value)
            self._timelabel.set_text(seconds_to_string(value/60))
        return True
