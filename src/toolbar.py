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
# Many code inspiration from gnome-music at the GNOME project

from gettext import gettext as _
from gi.repository import Gtk, GObject, Gdk, GLib

from lollypop.config import *
from lollypop.albumart import AlbumArt
from lollypop.search import SearchWidget
from lollypop.playlist import PlayListWidget
from lollypop.utils import translate_artist_name
from lollypop.popalbums import PopAlbums

class Toolbar():
	"""
		Init toolbar/headerbar ui
	"""
	def __init__(self):
		self._ui = Gtk.Builder()
		self._ui.add_from_resource('/org/gnome/Lollypop/headerbar.ui')
		self.header_bar = self._ui.get_object('header-bar')
		self.header_bar.set_custom_title(self._ui.get_object('title-box'))
		
		self._prev_btn = self._ui.get_object('previous_button')
		self._play_btn = self._ui.get_object('play_button')
		self._next_btn = self._ui.get_object('next_button')
		self._play_image = self._ui.get_object('play_image')
		self._pause_image = self._ui.get_object('pause_image')

		Objects["progress"] = self._ui.get_object('progress_scale')
		Objects["progress"].set_sensitive(False)
		Objects["time"] = self._ui.get_object('playback')
		self._total_time_label = self._ui.get_object('duration')
		
		self._title_label = self._ui.get_object('title')
		self._artist_label = self._ui.get_object('artist')
		self._cover = self._ui.get_object('cover')
		infobox = self._ui.get_object('infobox')	
		infobox.connect("button-press-event", self._pop_albums)
		self._popalbums = PopAlbums()
		self._popalbums.set_relative_to(infobox)
	
		Objects["player"].connect("playback-status-changed", self._playback_status_changed)
		Objects["player"].connect("current-changed", self.update_toolbar)
		Objects["player"].connect("cover-changed", self._update_cover)

		self._shuffle_btn = self._ui.get_object('shuffle-button')
		self._shuffle_btn.connect("toggled", self._shuffle_update)

		self._party_btn = self._ui.get_object('party-button')
		self._party_btn.connect("toggled", self._on_party_btn_toggled)

		Objects["progress"].connect('button-release-event', self._on_progress_scale_button)

		self._prev_btn.connect('clicked', self._on_prev_btn_clicked)
		self._play_btn.connect('clicked', self._on_play_btn_clicked)
		self._next_btn.connect('clicked', self._on_next_btn_clicked)
		
		self._view_genres_btn = self._ui.get_object('genres_button')
		self._view_genres_btn.set_active(Objects["settings"].get_value('hide-genres'))

		search_button = self._ui.get_object('search-button')
		search_button.connect("clicked", self._on_search_btn_clicked)
		self._search = SearchWidget()
		self._search.set_relative_to(search_button)

		playlist_button = self._ui.get_object('playlist-button')
		playlist_button.connect("clicked", self._on_playlist_btn_clicked)
		self._playlist = PlayListWidget()
		self._playlist.set_relative_to(playlist_button)

		self.header_bar.set_show_close_button(True)

	"""
		Return view genres button
	"""
	def get_view_genres_btn(self):
		return self._view_genres_btn

	"""
		Update toolbar items with track_id informations:
			- Cover
			- artist/title
			- reset progress bar
			- update time/total labels
	"""
	def update_toolbar(self, obj, track_id):
		if track_id == None:
			self._cover.hide()
			Objects["time"].hide()
			self._total_time_label.hide()
			self._prev_btn.set_sensitive(False)
			Objects["progress"].set_sensitive(False)
			self._play_btn.set_sensitive(False)
			self._next_btn.set_sensitive(False)
			self._title_label.set_text("")
			self._artist_label.set_text("")
		else:
			album_id = Objects["tracks"].get_album_id(track_id)
			art = Objects["art"].get(album_id,  ART_SIZE_SMALL)
			if art:
				self._cover.set_from_pixbuf(art)
				self._cover.show()
			else:
				self._cover.hide()
			
			title = Objects["tracks"].get_name(track_id)
			artist = Objects["tracks"].get_artist_name(track_id)
			artist = translate_artist_name(artist)
			self._title_label.set_text(title)
			self._artist_label.set_text(artist)
			Objects["progress"].set_value(0.0)
			duration = Objects["tracks"].get_length(track_id)
			Objects["progress"].set_range(0.0, duration * 60)
			self._total_time_label.set_text(Objects["player"].seconds_to_string(duration))
			self._total_time_label.show()
			Objects["time"].set_text("0:00")
			Objects["time"].show()

#######################
# PRIVATE             #
#######################
	"""
		Pop albums from current artist
	"""
	def _pop_albums(self, widget, data):
		track_id = Objects["player"].get_current_track_id()
		if track_id != -1:
			album_id = Objects["tracks"].get_album_id(track_id)
			artist_id = Objects["albums"].get_artist_id(album_id)
			self._popalbums.show()
			GLib.idle_add(self._popalbums.populate, artist_id)

	"""
		Update cover for album_id
	"""
	def _update_cover(self, widget, album_id):
		current_track_id = Objects["player"].get_current_track_id()
		current_album_id = Objects["tracks"].get_album_id(current_track_id)
		if current_album_id == album_id:
			self._cover.set_from_pixbuf(Objects["art"].get(album_id, ART_SIZE_SMALL))

	"""
		Callback for progress bar button
		Seek player to scale value
	"""	
	def _on_progress_scale_button(self, scale, data):
		Objects["player"].seek(scale.get_value()/60)
	
	"""
		Update buttons and progress bar
	"""
	def _playback_status_changed(self, obj):
		playing = Objects["player"].is_playing()

		Objects["progress"].set_sensitive(playing)
		if playing:
			self._change_play_btn_status(self._pause_image, _("Pause"))
			self._prev_btn.set_sensitive(True)
			self._play_btn.set_sensitive(True)
			self._next_btn.set_sensitive(True)
		else:
			self._change_play_btn_status(self._play_image, _("Play"))

	"""
		Previous track on prev button clicked
	"""		
	def _on_prev_btn_clicked(self, obj):
		Objects["player"].prev()

	"""
		Play/Pause on play button clicked
	"""		
	def _on_play_btn_clicked(self, obj):
		if Objects["player"].is_playing():
			Objects["player"].pause()
			self._change_play_btn_status(self._play_image, _("Play"))
		else:
			Objects["player"].play()
			self._change_play_btn_status(self._pause_image, _("Pause"))

	"""
		Next track on next button clicked
	"""		
	def _on_next_btn_clicked(self, obj):
		Objects["player"].next()		
	
	"""
		Show search widget on search button clicked
	"""
	def _on_search_btn_clicked(self, obj):
		self._search.show()
		
	"""
		Show playlist widget on playlist button clicked
	"""
	def _on_playlist_btn_clicked(self, obj):
		self._playlist.show()

	"""
		Update play button with image and status as tooltip
	"""
	def _change_play_btn_status(self, image, status):
		self._play_btn.set_image(image)
		self._play_btn.set_tooltip_text(status)

	"""
		Set shuffle mode on if shuffle button active
	"""
	def _shuffle_update(self, obj):
		Objects["player"].set_shuffle(self._shuffle_btn.get_active())

	"""
		Set party mode on if party button active
	"""
	def _on_party_btn_toggled(self, obj):
		settings = Gtk.Settings.get_default()
		active = self._party_btn.get_active()
		self._shuffle_btn.set_sensitive(not active)
		settings.set_property("gtk-application-prefer-dark-theme", active)
		Objects["player"].set_party(active)
