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
* 0.8.7:
  - Rewrite artist view
  - Add new queue options
* 0.8.6:
  - Fix cover popup placement
  - Fix empty covers in notifications
* 0.8.5:
  - Many speed improvements
* 0.8.4:
  - Fix layout when album grid not full
  - Fix album widgets sizing
* 0.8.3:
  - Make genres/artists list resizable
  - Fix a bug when clicking in empty playlist
* 0.8.2:
  - Fix regression in artist naming
  - Fix bug with some gtk themes
  - Add an option to continue playback when window is closed

* 0.8.1:
  - Handle compilations, albums with main artist and performers
  - Add a settings dialog
  - Add Opus support
  - Don't stop playing on End Of Stream

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

ARCHLINUX:

Available in Aur

OPENSUSE USERS:

https://build.opensuse.org/project/repository_state/home:gnumdk31/openSUSE_13.2

FEDORA USERS:

https://copr.fedoraproject.org/coprs/gnumdk/lollypop/

DEBIAN/UBUNTU USERS:
https://github.com/gnumdk/lollypop-data/raw/master/lollypop_0.8.6-1_amd64.deb
