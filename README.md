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
