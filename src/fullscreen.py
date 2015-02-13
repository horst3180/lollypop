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

from gi.repository import GObject, Gtk, GLib, GdkPixbuf
from gettext import gettext as _

from lollypop.define import *
from lollypop.utils import seconds_to_string

"""
	Show a fullscreen window showing current track context
"""
class FullScreen(Gtk.Window):

	"""
		Init window and set transient for parent
		@param: parent as Gtk.window
	"""
	def __init__(self, parent):
		Gtk.Window.__init__(self)
		self._timeout = None
		self._seeking = False
		self.set_transient_for(parent)
		self._ui = Gtk.Builder()
		self._ui.add_from_resource('/org/gnome/Lollypop/FullScreen.ui')
		main_widget = self._ui.get_object('fs')
		self.add(main_widget)
		self._prev_btn = self._ui.get_object('prev_btn')
		self._prev_btn.connect('clicked', self._on_prev_btn_clicked)
		self._play_btn = self._ui.get_object('play_btn')
		self._play_btn.connect('clicked', self._on_play_btn_clicked)
		self._next_btn = self._ui.get_object('next_btn')
		self._next_btn.connect('clicked', self._on_next_btn_clicked)
		self._play_image = self._ui.get_object('play_image')
		self._pause_image = self._ui.get_object('pause_image')
		close_btn = self._ui.get_object('close_btn')
		close_btn.connect('clicked', self._destroy)
		self._cover = self._ui.get_object('cover')
		self._title = self._ui.get_object('title')
		self._artist = self._ui.get_object('artist')
		self._album = self._ui.get_object('album')
		
		self._progress = self._ui.get_object('progress_scale')
		self._progress.set_sensitive(False)
		self._progress.connect('button-release-event', self._on_progress_release_button)
		self._progress.connect('button-press-event', self._on_progress_press_button)
		self._timelabel = self._ui.get_object('playback')
		self._total_time_label = self._ui.get_object('duration')

	"""
		Init signals, set color and go party mode if nothing is playing
	"""
	def do_show(self):
		is_playing = Objects.player.is_playing()
		Objects.player.connect("current-changed", self._on_current_changed)
		Objects.player.connect("status-changed", self._on_status_changed)
		if not Objects.player.is_party():
			settings = Gtk.Settings.get_default()
			settings.set_property("gtk-application-prefer-dark-theme", True)
			if not is_playing:
				Objects.player.set_party(True)
		if is_playing:
			self._change_play_btn_status(self._pause_image, _("Pause"))
		self._on_current_changed(Objects.player)
		if is_playing and not self._timeout:
			self._timeout = GLib.timeout_add(1000, self._update_position)
		Gtk.Window.do_show(self)
		self.fullscreen()

	"""
		Remove signals and unset color
	"""
	def  do_hide(self):
		Objects.player.disconnect_by_func(self._on_current_changed)
		Objects.player.disconnect_by_func(self._on_status_changed)
		if not Objects.player.is_party():
			settings = Gtk.Settings.get_default()
			settings.set_property("gtk-application-prefer-dark-theme", False)
		if self._timeout:
			GLib.source_remove(self._timeout)
			self._timeout = None

#######################
# PRIVATE             #
#######################
	"""
		Update View for current track
			- Cover
			- artist/title
			- reset progress bar
			- update time/total labels
		@param player as Player
	"""
	def _on_current_changed(self, player):
		if player.current.id == None:
			self._cover.hide()
			self._timelabel.hide()
			self._total_time_label.hide()
			self._prev_btn.set_sensitive(False)
			self._progress.set_sensitive(False)
			self._play_btn.set_sensitive(False)
			self._next_btn.set_sensitive(False)
			self._title.set_text("")
			self._artist.set_text("")
			self._album.set_text("")
		else:
			art = Objects.art.get(player.current.album_id,  ART_SIZE_MONSTER)
			if art:
				self._cover.set_from_pixbuf(art)
				self._cover.show()
			else:
				self._cover.hide()
			
			self._title.set_text(player.current.title)
			self._artist.set_text(player.current.artist)
			self._album.set_text(player.current.album)
			self._progress.set_value(1.0)
			self._progress.set_range(0.0, player.current.duration * 60)
			self._total_time_label.set_text(seconds_to_string(player.current.duration))
			self._total_time_label.show()
			self._timelabel.set_text("0:00")
			self._timelabel.show()

	"""
		Go to prev track
		@param widget as Gtk.Button
	"""
	def _on_prev_btn_clicked(self, widget):
		Objects.player.prev()

	"""
		Play/pause
		@param widget as Gtk.Button
	"""
	def _on_play_btn_clicked(self, widget):
		if Objects.player.is_playing():
			Objects.player.pause()
			widget.set_image(self._ui.get_object('play_image'))
		else:
			Objects.player.play()
			widget.set_image(self._ui.get_object('pause_image'))

	"""
		Go to next track
		@param widget as Gtk.Button
	"""
	def _on_next_btn_clicked(self, widget):
		Objects.player.next()

	"""
		Update buttons and progress bar
		@param obj as unused
	"""
	def _on_status_changed(self, obj):
		is_playing = Objects.player.is_playing()
		self._progress.set_sensitive(is_playing)
		if is_playing and not self._timeout:
			self._timeout = GLib.timeout_add(1000, self._update_position)
			self._change_play_btn_status(self._pause_image, _("Pause"))
			self._prev_btn.set_sensitive(True)
			self._play_btn.set_sensitive(True)
			self._next_btn.set_sensitive(True)
		elif not is_playing and self._timeout:
			GLib.source_remove(self._timeout)
			self._timeout = None
			self._change_play_btn_status(self._play_image, _("Play"))

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
		Update play button with image and status as tooltip
		@param image as Gtk.Image
		@param status as str
	"""
	def _change_play_btn_status(self, image, status):
		self._play_btn.set_image(image)
		self._play_btn.set_tooltip_text(status)

	"""
		Update progress bar position
		@param value as int
	"""
	def _update_position(self, value = None):
		if not self._seeking:
			if value == None:
				value = Objects.player.get_position_in_track()/1000000
			self._progress.set_value(value)
			self._timelabel.set_text(seconds_to_string(value/60))
		return True

	"""
		Destroy self
		@param widget as Gtk.Button
	"""
	def _destroy(self, widget):
		self.destroy()
