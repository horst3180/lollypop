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

from gi.repository import Gtk, Gdk, GObject, GdkPixbuf, Gio, Pango, PangoCairo
import cairo
import os, json
import urllib.request
import urllib.parse
from math import pi
from random import uniform
from mutagen import File as Idtag

from lollypop.config import *
from lollypop.database import Database

"""
	Manage album's arts
"""
class AlbumArt: 

	_CACHE_PATH = os.path.expanduser ("~") +  "/.cache/lollypop"
	_mimes = [ "jpeg", "jpg", "png", "gif" ]
	
	"""
		Create cache path
	"""	
	def __init__(self):

		if not os.path.exists(self._CACHE_PATH):
			try:
				os.mkdir(self._CACHE_PATH)
			except:
				print("Can't create %s" % self._CACHE_PATH)

	"""
		get cover cache path for album_id
		@param album id as int, size as int
		@return cover path as string
	"""
	def get_path(self, album_id, size):
		album_path = Objects["albums"].get_path(album_id)
		art_path = "%s/%s_%s.jpg" % (self._CACHE_PATH, album_path.replace("/", "_"), size)
		if not os.path.exists(art_path):
			self.get(album_id, size)
		return art_path
	
	"""
		Look for covers in dir, folder.jpg if exist, any supported image otherwise
		@param directory path as string
		@return cover file path as string
	"""
	def get_art_path(self, directory):
		try:
			if os.path.exists(directory+"/folder.jpg"):
				return directory+"/folder.jpg"
		
			for file in os.listdir (directory):
				lowername = file.lower()
				supported = False
				for mime in self._mimes:
					if lowername.endswith(mime):
						supported = True
						break	
				if (supported):
					return "%s/%s" % (directory, file)

			return None
		except:
		    pass
	
	"""
		Return pixbuf for album_id
		@param album id as int, pixbuf size as int
		return: pixbuf
	"""
	def get(self, album_id, size):
		album_path = Objects["albums"].get_path(album_id)
		CACHE_PATH = "%s/%s_%s.jpg" % (self._CACHE_PATH, album_path.replace("/", "_"), size)
		cached = True
		pixbuf = None
		try:
			if not os.path.exists(CACHE_PATH):
				path = self.get_art_path(album_path)
				if path:
					pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale (path,
																	  size, size, False)
					pixbuf.savev(CACHE_PATH, "jpeg", ["quality"], ["90"])
				else:
					# Try to get from tags
					try:
						for track_id in Objects["albums"].get_tracks(album_id):
							filepath = Objects["tracks"].get_path(track_id)
							filetag = Idtag(filepath, easy = False)
							for tag in filetag.tags:
								if tag.startswith("APIC:"):
									audiotag = filetag.tags[tag]
									# TODO check type by pref
									stream = Gio.MemoryInputStream.new_from_data(audiotag.data, None)
									pixbuf = GdkPixbuf.Pixbuf.new_from_stream_at_scale(stream, size,
																   							size,
															      							False,
																  							None)
									pixbuf.savev(CACHE_PATH, "jpeg", ["quality"], ["90"])
									return pixbuf
								elif tag == "covr":
									for data in filetag.tags["covr"]:
										stream = Gio.MemoryInputStream.new_from_data(data, None)
										pixbuf = GdkPixbuf.Pixbuf.new_from_stream_at_scale(stream, size,
																   							size,
															      							False,
																  							None)
										pixbuf.savev(CACHE_PATH, "jpeg", ["quality"], ["90"])
										return pixbuf
					except Exception as e:
						print(e)
						pass

					pixbuf = self._get_default_art(album_id, size)
			else:
				pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size (CACHE_PATH,
																 size, size)
			return pixbuf
			
		except Exception as e:
			print(e)
			return self._get_default_art(album_id, size)


	"""
		Remove cover from cache for album id
		@param album id as int, size as int
	"""
	def clean_cache(self, album_id, size):
		album_path = Objects["albums"].get_path(album_id)
		cache_path = "%s/%s_%s.jpg" % (self._CACHE_PATH, album_path.replace("/", "_"), size)
		if os.path.exists(cache_path):
			os.remove(cache_path)

	"""
		Get arts on google image corresponding to search
		@param search words as string
		@return [urls as string]
	"""
	def get_google_arts(self, search):
		try:
			response = urllib.request.urlopen("https://ajax.googleapis.com/ajax/services/search/images?&q=%s&v=1.0&start=0&rsz=8" %  urllib.parse.quote(search))
		except:
			return None

		data = response.read()
		decode = json.loads(data.decode("utf-8"))
		urls = []
		if not decode:
			return None
		for item in decode['responseData']['results']:
			urls.append(item['url'])
			
		return urls

#######################
# PRIVATE             #
#######################


	"""
		Construct a cover album based on album id
		@param album id as int
		@param pixbuf size as int
		@return pixbuf
	"""
	def _get_default_art(self, album_id, size):
		album_name = Objects["albums"].get_name(album_id)
		surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
		ctx = cairo.Context(surface)
		r = uniform(0.05, 0.9)
		g = uniform(0.05, 0.9)
		b = uniform(0.05, 0.9)
		ctx.set_source_rgba(r, g ,b, 1)
		ctx.move_to(0, 0)
		ctx.rectangle(0, 0, size, size)
		ctx.fill()
		ctx.save()
		ctx = cairo.Context(surface)
		layout = PangoCairo.create_layout(ctx)
		layout.set_markup('''<span foreground="white" font_desc="Sans %s"><b>%s</b></span>''' % (size/4, album_name[0]))
		char_width = layout.get_size()[0]/Pango.SCALE
		char_height = layout.get_size()[1]/Pango.SCALE
		ctx.move_to(size/2 - char_width/2, size/2 - char_height/2)
		ctx.save()
		PangoCairo.show_layout(ctx, layout)
		return Gdk.pixbuf_get_from_surface(surface, 0, 0, size, size)

