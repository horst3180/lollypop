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

Changes:
* 0.7.0:
  - Threaded interface
  - Cover art search
  - Context view by clicking on headerbar infobox
  - Able to hide genres column

Tarball: https://github.com/gnumdk/lollypop-data

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
