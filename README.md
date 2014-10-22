Lollypop 0.5.2
========================

Lollypop is a new GNOME music playing application.

It provides:
- mp3/4, ogg and flac.
- Genre/Cover browsing
- Genre/Artist/Cover browsing
- Search
- Main playlist (called queue in other apps)
- Party mode
- Replay gain

Changes:
* 0.6 (not released yet):
  - Add an gsetting option to add customs music paths
  - Handle album compilations
  - Fix performance issues
  - Better widgets for search and playlist
  - Handle specials prefix for artists
  - Gapless playing
* 0.5.2:
  - Fix Ubuntu notifications (cover not working for now)
  - Fix database reinit

* 0.5.1: 
  - Fix Ubuntu install

Tarball: https://github.com/gnumdk/lollypop-data/raw/master/lollypop-0.5.2.tar.xz

![Lollypop screenshot](https://github.com/gnumdk/lollypop-data/raw/master/lollypop1.png)
![Lollypop screenshot](https://github.com/gnumdk/lollypop-data/raw/master/lollypop2.png)
![Lollypop screenshot](https://github.com/gnumdk/lollypop-data/raw/master/lollypop3.png)

TODO:
- Gapless playback 
- Extract covers from files (is mutagen able?)
- Missing covers in notify-osd
- Drag & Drop in playlist popup (help really welcome)

Patchs are welcome ;)


=== Depends on ===
- gtk3
- intltool (make)
- itstool (make)
- python (make)
- python-cairo
- python-dbus
- python-gobject
- python-mutagen



=== Building from git ===

$ git clone https://github.com/gnumdk/lollypop.git

$ cd lollypop

$ ./autogen.sh

$ make

\# make install


UBUNTU USERS:
You need to install mutagen last version... Python3-mutagen is missing from Ubuntu
