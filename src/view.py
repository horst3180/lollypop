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

from gi.repository import Gtk, GObject, Gdk
from gettext import gettext as _

from lollypop.config import Objects
from lollypop.database import Database
from lollypop.widgets import *
from lollypop.utils import translate_artist_name

class LoadingView(Gtk.Grid):
	def __init__(self):
		Gtk.Grid.__init__(self)
		self._ui = Gtk.Builder()
		self._ui.add_from_resource('/org/gnome/Lollypop/Loading.ui')
		self.set_property('halign', Gtk.Align.CENTER)
		self.set_property('valign', Gtk.Align.CENTER)
		self.set_vexpand(True)
		self.set_hexpand(True)
		self._label = self._ui.get_object('label')
		self._label.set_label(_("Loading please wait..."))
		self.add(self._label)
		self.show_all()
	def remove_signals(self):
		pass

	
class View(Gtk.Grid):
	def __init__(self):
		Gtk.Grid.__init__(self)
		self.set_property("orientation", Gtk.Orientation.VERTICAL)
		self.set_border_width(0)
		# Current object, used to handle context/content view
		self._object_id = None

		Objects["player"].connect("current-changed", self.current_changed)
		Objects["player"].connect("cover-changed", self.cover_changed)

	def remove_signals(self):
		Objects["player"].disconnect_by_func(self.current_changed)
		Objects["player"].disconnect_by_func(self.cover_changed)


	"""
		Current song changed
		Update context and content
	"""
	def current_changed(self, widget, track_id):
		self._update_content()
		self._update_context()

	"""
		Update album cover in view
	"""
	def cover_changed(self, widget, album_id):
		pass
		
#######################
# PRIVATE             #
#######################

	"""
		Update content view
	"""
	def _update_content(self):
		pass

	"""
		Update context view
	"""
	def _update_context(self):
		pass


class ArtistView(View):

	"""
		Init ArtistView ui with a scrolled grid of AlbumWidgetSongs
	"""
	def __init__(self, artist_id, genre_id):
		View.__init__(self)
		self._genre_id = genre_id
		self.set_property("orientation", Gtk.Orientation.VERTICAL)
		self._ui = Gtk.Builder()
		self._ui.add_from_resource('/org/gnome/Lollypop/ArtistView.ui')

		self._object_id = artist_id
		artist_name = Objects["artists"].get_name(artist_id)
		artist_name = translate_artist_name(artist_name)
		self._ui.get_object('artist').set_label(artist_name)

		self._albumbox = Gtk.Grid()
		if Objects["settings"].get_value('dark-view'):
			self._albumbox.get_style_context().add_class('black')
		self._albumbox.set_property("orientation", Gtk.Orientation.VERTICAL)
		self._scrolledWindow = Gtk.ScrolledWindow()
		self._scrolledWindow.set_vexpand(True)
		self._scrolledWindow.set_hexpand(True)
		self._scrolledWindow.set_policy(Gtk.PolicyType.NEVER,
						Gtk.PolicyType.AUTOMATIC)
		self._scrolledWindow.add(self._albumbox)

		self.add(self._ui.get_object('ArtistView'))
		self.add(self._scrolledWindow)
		self.show_all()

	"""
		Populate the view
	"""
	def populate(self):
		if self._genre_id == -1:
			albums = Objects["albums"].get_ids(self._object_id, None)
		else:
			albums = Objects["albums"].get_ids(self._object_id, self._genre_id)
		for album_id in albums:
			self._populate_content(album_id)

	"""
		Update album cover in view
	"""
	def cover_changed(self, widget, album_id):
		for widget in self._albumbox.get_children():
			widget.update_cover(album_id)

#######################
# PRIVATE             #
#######################

	"""
		Update the content view
	"""
	def _update_content(self):
		track_id = Objects["player"].get_current_track_id()
		artist_id = Objects["tracks"].get_artist_id(track_id)
		if self._albumbox and artist_id == self._albumbox.get_id():
			for widget in self._albumbox.get_children():
				widget.update_tracks()


	"""
		populate content view with album_id
	"""
	def _populate_content(self, album_id):
		widget = AlbumWidgetSongs(album_id, self._genre_id)
		self._albumbox.add(widget)
		widget.show()	

	"""
		Clean content view
	"""
	def _clean_content(self):
		for widget in self._albumbox.get_children():
			widget.hide()
			widget.destroy()

class AlbumView(View):

	"""
		Init album view ui with a scrolled flow box and a scrolled context view
	"""
	def __init__(self, genre_id):
		View.__init__(self)
		self._genre_id = genre_id
		self._albumsongs = None

		self._albumbox = Gtk.FlowBox()
		if Objects["settings"].get_value('dark-view'):
			self._albumbox.get_style_context().add_class('black')
		self._albumbox.set_homogeneous(True)
		self._albumbox.set_selection_mode(Gtk.SelectionMode.NONE)
		self._albumbox.connect("child-activated", self._on_album_activated)
		self._albumbox.set_max_children_per_line(100)
		self._scrolledWindow = Gtk.ScrolledWindow()
		self._scrolledWindow.set_vexpand(True)
		self._scrolledWindow.set_hexpand(True)
		self._scrolledWindow.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
		self._scrolledWindow.add(self._albumbox)
		self._scrolledWindow.show_all()

		self._scrolledContext = Gtk.ScrolledWindow()
		self._scrolledContext.set_min_content_height(250)
		self._scrolledContext.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
		self._viewport = Gtk.Viewport()
		Gtk.Container.add(self._scrolledContext ,self._viewport)
		separator = Gtk.Separator()
		separator.show()
		
		self.add(self._scrolledWindow)
		self.add(separator)
		self.add(self._scrolledContext)
		self.show()

	"""
		Populate albums
	"""	
	def populate(self):
		if self._genre_id == -1:
			albums = Objects["albums"].get_ids()
		else:
			albums = Objects["albums"].get_compilations(self._genre_id)
			albums += Objects["albums"].get_ids(None, self._genre_id)
		GLib.idle_add(self._add_albums, albums)
	
	"""
		Populate albums with popular ones
	"""			
	def populate_popular(self):
		for album_id in Objects["albums"].get_populars():
			widget = AlbumWidget(album_id)
			widget.show()
			self._albumbox.insert(widget, -1)

	"""
		Update album cover in view
	"""
	def cover_changed(self, widget, album_id):
		self._albumsongs.update_cover(album_id)
		for child in self._albumbox.get_children():
			for widget in child.get_children():
				widget.update_cover(album_id)

#######################
# PRIVATE             #
#######################
	"""
		Update the context view
	"""
	def _update_context(self):
		track_id = Objects["player"].get_current_track_id()
		album_id = Objects["tracks"].get_album_id(track_id)
		if self._albumsongs and album_id == self._albumsongs.get_id():
			self._albumsongs.update_tracks(track_id)

	"""
		populate context view
	"""
	def _populate_context(self, album_id):
		self._albumsongs = AlbumWidgetSongs(album_id, self._genre_id)
		self._viewport.add(self._albumsongs)
		self._scrolledContext.show_all()

	"""
		Clean context view
	"""
	def _clean_context(self):
		if self._albumsongs:
			self._viewport.remove(self._albumsongs)
			self._albumsongs.destroy()
			self._albumsongs = None
			
	"""
		Show Context view for activated album
	"""
	def _on_album_activated(self, flowbox, child):
		if self._albumsongs and self._object_id == child.get_child().get_id():
			self._clean_context()
			self._scrolledContext.hide()
		else:
			if self._albumsongs:
				self._clean_context()
			self._object_id = child.get_child().get_id()
			self._populate_context(self._object_id)
			self._scrolledContext.show_all()		
	
	"""
		Add albums using gmainloop
	"""
	def _add_albums_mainloop(self, albums_id):
		if len(albums_id) > 0:
			widget = AlbumWidget(albums_id[0])
			widget.show()
			self._albumbox.insert(widget, -1)
			albums_id.pop(0)
			GLib.idle_add(self._add_albums, albums_id)
	"""
		Add albums with current genre to the flowbox
		arg: int
	"""
	def _add_albums(self, albums_id):
		i = 1
		# We first load somes albums to init view and then let mainloop populate the view
		for album in albums_id:
			widget = AlbumWidget(album)
			widget.show()
			self._albumbox.insert(widget, -1)
			i += 1
			if i > 40:
				GLib.idle_add(self._add_albums_mainloop, albums_id[i:], priority=GLib.PRIORITY_LOW)
				break
