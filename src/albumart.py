#!/usr/bin/python
# Copyright (c) 2014-2015 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
# Copyright (c) 2013 Vadim Rutkovsky <vrutkovs@redhat.com>
# Copyright (c) 2013 Arnel A. Borja <kyoushuu@yahoo.com>
# Copyright (c) 2013 Seif Lotfy <seif@lotfy.com>
# Copyright (c) 2013 Guillaume Quintard <guillaume.quintard@gmail.com>
# Copyright (c) 2013 Lubosz Sarnecki <lubosz@gmail.com>
# Copyright (c) 2013 Sai Suman Prayaga <suman.sai14@gmail.com>
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

from gi.repository import Gtk, Gdk, GdkPixbuf, Gio
import cairo
import os
import re
import json
import urllib.request
import urllib.parse
from math import pi
import mutagen
import base64

from lollypop.define import Objects, ArtSize


# Manage album's arts
class AlbumArt:

    _CACHE_PATH = os.path.expanduser("~") + "/.cache/lollypop"
    _mimes = ["jpeg", "jpg", "png", "gif"]

    """
        Create cache path
    """
    def __init__(self):
        self._favorite = Objects.settings.get_value(
                                                'favorite-cover').get_string()
        if not os.path.exists(self._CACHE_PATH):
            try:
                os.mkdir(self._CACHE_PATH)
            except:
                print("Can't create %s" % self._CACHE_PATH)

    """
        get cover cache path for album_id
        @param album id as int, size as int
        @return cover path as string or None if no cover
    """
    def get_path(self, album_id, size):
        path = None
        try:
            path = self._get_cache_path(album_id)
            CACHE_PATH_JPG = "%s/%s_%s.jpg" % (self._CACHE_PATH, path, size)
            if os.path.exists(CACHE_PATH_JPG):
                return CACHE_PATH_JPG
            else:
                self.get(album_id, size)
                if os.path.exists(CACHE_PATH_JPG):
                    return CACHE_PATH_JPG
                else:
                    return None
        except Exception as e:
            print("AlbumArt::get_path(): %s" %e, ascii(path))
            return None

    """
        Look for covers in dir
        any supported image otherwise
        @param album id as int
        @return cover file path as string
    """
    def get_art_path(self, album_id, sql=None):
        album_path = Objects.albums.get_path(album_id, sql)
        album_name = Objects.albums.get_name(album_id, sql)
        artist_name = Objects.albums.get_artist_name(album_id, sql)
        try:
            if os.path.exists(album_path + "/" + self._favorite):
                return album_path + "/" + self._favorite
            # Used when having muliple albums in same folder
            elif os.path.exists(album_path + "/" + artist_name +
                                "_" + album_name + ".jpg"):
                return album_path + "/" +\
                       artist_name + "_" + album_name + ".jpg"

            for file in os.listdir(album_path):
                lowername = file.lower()
                supported = False
                for mime in self._mimes:
                    if lowername.endswith(mime):
                        supported = True
                        break
                if (supported):
                    return "%s/%s" % (album_path, file)

            return None
        except Exception as e:
            print("AlbumArt::get_art_path(): %s" % e)

    """
        Return pixbuf for album_id, covers are cached as jpg.
        @param album id as int, pixbuf size as int
        return: pixbuf
    """
    def get(self, album_id, size):
        path = self._get_cache_path(album_id)
        CACHE_PATH_JPG = "%s/%s_%s.jpg" % (self._CACHE_PATH, path, size)
        pixbuf = None

        try:
            # Look in cache
            if os.path.exists(CACHE_PATH_JPG):
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(CACHE_PATH_JPG,
                                                                size,
                                                                size)
            else:
                path = self.get_art_path(album_id)
                # Look in album folder
                if path:
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(path,
                                                                     size,
                                                                     size,
                                                                     False)
                # Try to get from tags
                else:
                    try:
                        for track_id in Objects.albums.get_tracks(album_id):
                            pixbuf = self._pixbuf_from_tags(track_id, size)
                            # We found a cover in tags
                            if pixbuf:
                                break
                    except Exception as e:
                        print(e)
                        return self._make_icon_frame(
                                            self._get_default_icon(size),
                                            size
                                                    )

                # No cover, use default one
                if not pixbuf:
                    pixbuf = self._get_default_icon(size)
                else:
                    # Gdk < 3.15 was missing save method
                    # > 3.15 is missing savev method
                    try:
                        pixbuf.save(CACHE_PATH_JPG, "jpeg",
                                    ["quality"], ["90"])
                    except:
                        pixbuf.savev(CACHE_PATH_JPG, "jpeg",
                                     ["quality"], ["90"])

            return self._make_icon_frame(pixbuf, size)

        except Exception as e:
            print(e)
            return self._make_icon_frame(self._get_default_icon(size), size)

    """
        Remove cover from cache for album id
        @param album id as int
    """
    def clean_cache(self, album_id):
        path = self._get_cache_path(album_id)
        for f in os.listdir(self._CACHE_PATH):
            if re.search('%s_.*\.jpg' % path, f):
                os.remove(os.path.join(self._CACHE_PATH, f))

    """
        Save pixbuf for album id
        @param pixbuf as Gdk.Pixbuf
        @param album id as int
    """
    def save_art(self, pixbuf, album_id):
        album_path = Objects.albums.get_path(album_id)
        path_count = Objects.albums.get_path_count(album_path)
        album_name = Objects.albums.get_name(album_id)
        artist_name = Objects.albums.get_artist_name(album_id)
        try:
            # Many albums with same path, suffix with artist_album name
            if path_count > 1:
                artpath = album_path + "/" +\
                          artist_name + "_" +\
                          album_name + ".jpg"
                if os.path.exists(album_path+"/"+self._favorite):
                    os.remove(album_path+"/"+self._favorite)
            else:
                artpath = album_path+"/"+self._favorite

            # Gdk < 3.15 was missing save method
            try:
                pixbuf.save(artpath, "jpeg", ["quality"], ["90"])
            # > 3.15 is missing savev method :(
            except:
                pixbuf.savev(artpath, "jpeg", ["quality"], ["90"])
        except Exception as e:
            print("AlbumArt::save_art(): %s" % e)

    """
        Get arts on google image corresponding to search
        @param search words as string
        @return [urls as string]
    """
    def get_google_arts(self, search):
        try:
            response = urllib.request.urlopen("https://ajax.googleapis.com/"
                                              "ajax/services/search/images"
                                              "?&q=%s&v=1.0&start=0&rsz=8" %
                                              urllib.parse.quote(search))
        except Exception as e:
            print(e)
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
        Return cover from tags
        @param track id as int
        @param size as int
    """
    def _pixbuf_from_tags(self, track_id, size):
        pixbuf = None
        filepath = Objects.tracks.get_path(track_id)
        filetag = mutagen.File(filepath, easy=False)
        for tag in filetag.tags:
            if isinstance(tag, tuple):
                if tag[0] == "METADATA_BLOCK_PICTURE":
                    image = mutagen.flac.Picture(
                                            base64.standard_b64decode(tag[1]))
                    stream = Gio.MemoryInputStream.new_from_data(image.data,
                                                                 None)
                    pixbuf = GdkPixbuf.Pixbuf.new_from_stream_at_scale(stream,
                                                                   size,
                                                                   size,
                                                                   False,
                                                                   None)
                    break
            elif tag.startswith("APIC:"):
                audiotag = filetag.tags[tag]
                # TODO check type by pref
                stream = Gio.MemoryInputStream.new_from_data(audiotag.data,
                                                             None)
                pixbuf = GdkPixbuf.Pixbuf.new_from_stream_at_scale(stream,
                                                                   size,
                                                                   size,
                                                                   False,
                                                                   None)
                break
            elif tag == "covr":
                data = filetag.tags["covr"]
                if len(data) > 0:
                    stream = Gio.MemoryInputStream.new_from_data(data[0],
                                                                 None)
                    pixbuf = GdkPixbuf.Pixbuf.new_from_stream_at_scale(
                                                                   stream,
                                                                   size,
                                                                   size,
                                                                   False,
                                                                   None)
                    break
        return pixbuf

    """
        Get a uniq string for album
        @param album id as int
    """
    def _get_cache_path(self, album_id):
        path = Objects.albums.get_name(album_id) + "_" + \
               Objects.albums.get_artist_name(album_id) + "_" + \
               Objects.albums.get_genre_name(album_id)
        return path[0:240].replace("/", "_")

    """
        Draw an icon frame around pixbuf,
        code forked Gnome Music, see copyright header
        @param: pixbuf source as Gdk.Pixbuf
        @param: size as int
    """
    def _make_icon_frame(self, pixbuf, size):
        # No border on small covers, looks ugly
        if size < ArtSize.BIG or not\
           Objects.settings.get_value('stylized-covers'):
            return pixbuf

        border = 3
        degrees = pi / 180
        radius = 3
        surface_size = size + border * 2
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                     surface_size, surface_size)
        ctx = cairo.Context(surface)
        ctx.new_sub_path()
        ctx.arc(surface_size - radius, radius,
                radius - 0.5, -90 * degrees, 0 * degrees)
        ctx.arc(surface_size - radius, surface_size - radius,
                radius - 0.5, 0 * degrees, 90 * degrees)
        ctx.arc(radius, surface_size - radius,
                radius - 0.5, 90 * degrees, 180 * degrees)
        ctx.arc(radius, radius, radius - 0.5, 180 * degrees, 270 * degrees)
        ctx.close_path()
        ctx.set_line_width(0.6)
        ctx.set_source_rgb(0.2, 0.2, 0.2)
        ctx.stroke_preserve()
        ctx.set_source_rgb(1, 1, 1)
        ctx.fill()
        border_pixbuf = Gdk.pixbuf_get_from_surface(surface, 0, 0,
                                                    surface_size,
                                                    surface_size)

        pixbuf.copy_area(0, 0,
                         size,
                         size,
                         border_pixbuf,
                         border, border)
        return border_pixbuf

    """
        Construct an empty cover album,
        code forked Gnome Music, see copyright header
        @param size as int
        @return pixbuf as Gdk.Pixbuf
    """
    def _get_default_icon(self, size):
        # get a small pixbuf with the given path
        icon_size = size / 4
        icon = Gtk.IconTheme.get_default().load_icon('folder-music-symbolic',
                                                     icon_size, 0)
        # create an empty pixbuf with the requested size
        result = GdkPixbuf.Pixbuf.new(icon.get_colorspace(),
                                      True,
                                      icon.get_bits_per_sample(),
                                      size,
                                      size)
        result.fill(0xffffffff)
        icon.composite(result,
                       icon_size * 3 / 2,
                       icon_size * 3 / 2,
                       icon_size,
                       icon_size,
                       icon_size * 3 / 2,
                       icon_size * 3 / 2,
                       1, 1,
                       GdkPixbuf.InterpType.NEAREST, 255)
        return result
