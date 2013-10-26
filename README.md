Pymp: A Gtk+ interface for MPlayer in Python
====
© Jay Dolan 2004-2013

https://github.com/jdolan/pymp

Introduction
----
Pymp is a simple Gtk+ interface for MPlayer. It supports any media type MPlayer does, and has basic media player features like:

 * Opening files on the command line: ```pymp *.mp3```
 * Open files or locations, i.e.: ```pymp http://x.com/foo.avi dvd://1```
 * Drag and drop files or folders to playlist
 * Remote commands (scripting):

```
pymp -remote pause
pymp -remote stop
pymp -remote play 12
pymp -remote status
pymp -remote seek 20
```
 
 * Simple playlist format:

```
find ~/ -name "*.mp3" > playlist.m3u
```

 * Auto save/restore last playlist
 * Continuous, random, and repeat play
 * Interactive progress bar
 * Find file in list: ```<ctrl+f>```
 * Really freakin' tiny

Credits
----
 * Matt Housh - the name pymp
 * Lucas Hazel - mplayer io, ui enhancements
 * Greg Harris - mplayer io, playback status

License
----
Pymp's released under the GPL. Improvements and feedback are very welcome. Contact me at *jay at jaydolan dot com*.


