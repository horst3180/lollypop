Lollypop
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
- Cover art downloader
- Context artist view

Changes:
* 0.8.1 (to be released soon):
  - Handle compilations, albums with main artist and performers
  - Add a settings dialog
  - Add Opus support

Tarball: https://github.com/gnumdk/lollypop-data

ArchLinux: lollypop is in AUR

![Lollypop screenshot](https://github.com/gnumdk/lollypop-data/raw/master/lollypop1.png)
![Lollypop screenshot](https://github.com/gnumdk/lollypop-data/raw/master/lollypop2.png)
![Lollypop screenshot](https://github.com/gnumdk/lollypop-data/raw/master/lollypop3.png)

TODO:
- Extract covers from files (is mutagen able?)
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
$ pip3 mutagen
