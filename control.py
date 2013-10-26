#!/usr/bin/env python

import pango, pygtk, gtk

HPADDING, VPADDING, PROG_WIDTH, PROG_HEIGHT = 12, 2, 150, 10

SEEK_STEP = 10

#
#  Provides navigational control to the current mplayer job.
#  Main widget: hbox
#
class Control:

	pymp, hbox, progBar = None, None, None

	#
	#  Creates and returns a control group for pymp.
	#
	def __init__(self, pymp):

		self.pymp = pymp
		self.PLAYSTATUS = 1

		prevImg = gtk.image_new_from_stock(gtk.STOCK_MEDIA_PREVIOUS, gtk.ICON_SIZE_MENU)
		prevImg.set_padding(HPADDING, VPADDING)

		prevBox = gtk.EventBox()
		prevBox.add(prevImg)
		prevBox.connect("button-press-event", self.pymp.playlist.prev)

		rewImg = gtk.image_new_from_stock(gtk.STOCK_MEDIA_REWIND, gtk.ICON_SIZE_MENU)
		rewImg.set_padding(HPADDING, VPADDING)

		rewBox = gtk.EventBox()
		rewBox.add(rewImg)
		rewBox.connect("button-press-event", self.seek, -1 * SEEK_STEP)

		# Play/pause button
		self.pseImg = gtk.image_new_from_stock(gtk.STOCK_MEDIA_PAUSE, gtk.ICON_SIZE_MENU)
		self.pseImg.set_padding(HPADDING, VPADDING)
		self.pseImg.show()

		self.plyImg = gtk.image_new_from_stock(gtk.STOCK_MEDIA_PLAY, gtk.ICON_SIZE_MENU)
		self.plyImg.set_padding(HPADDING, VPADDING)
		self.plyImg.show()

		self.pseBox = gtk.EventBox()
		self.pseBox.add(self.plyImg)
		self.pseBox.connect("button-press-event", self.playPause)

		stopImg = gtk.image_new_from_stock(gtk.STOCK_MEDIA_STOP, gtk.ICON_SIZE_MENU)
		stopImg.set_padding(HPADDING, VPADDING)

		stopBox = gtk.EventBox()
		stopBox.add(stopImg)
		stopBox.connect("button-press-event", self.pymp.playlist.stop)

		ffImg = gtk.image_new_from_stock(gtk.STOCK_MEDIA_FORWARD, gtk.ICON_SIZE_MENU)
		ffImg.set_padding(HPADDING, VPADDING)

		ffBox = gtk.EventBox()
		ffBox.add(ffImg)
		ffBox.connect("button-press-event", self.seek, SEEK_STEP)

		nextImg = gtk.image_new_from_stock(gtk.STOCK_MEDIA_NEXT, gtk.ICON_SIZE_MENU)
		nextImg.set_padding(HPADDING, VPADDING)

		nextBox = gtk.EventBox()
		nextBox.add(nextImg)
		nextBox.connect("button-press-event", self.pymp.playlist.next)

		progBar = gtk.ProgressBar()
		progBar.set_size_request(PROG_WIDTH, PROG_HEIGHT)

		font = pango.FontDescription("8")
		progBar.modify_font(font)

		progBox = gtk.EventBox()
		progBox.add(progBar)
		progBox.connect("button-press-event", self.seekPercent)

		hbox = gtk.HBox(False, 0)
		hbox.pack_start(prevBox, False, False, 0)
		hbox.pack_start(rewBox, False, False, 0)
		hbox.pack_start(self.pseBox, False, False, 0)
		hbox.pack_start(stopBox, False, False, 0)
		hbox.pack_start(ffBox, False, False, 0)
		hbox.pack_start(nextBox, False, False, 0)
		hbox.pack_start(progBox, True, True, 0)

		target = [("text/uri-list", 0, 0)]  #external drag/drop
		hbox.drag_dest_set(gtk.DEST_DEFAULT_ALL, target, gtk.gdk.ACTION_COPY)
		hbox.connect("drag-data-received", self.dragReceived)
		self.progBar, self.hbox = progBar, hbox

	#
	#  Seeks secs seconds in the current target.
	#
	def seek(self, widget, event, secs):
		self.pymp.mplayer.seek(secs)
		return True

	#
	#  Pauses the current mplayer job.
	#
	def playPause(self, widget, event):
		self.pymp.mplayer.pause()
		return True

	#
	#  Switch the status of the pause/play button
	#
	def switchPlayStatus(self, status):

		if status == 1 and self.PLAYSTATUS == 1:
			self.pseBox.remove(self.plyImg)
			self.pseBox.add(self.pseImg)
			self.PLAYSTATUS = 0
		elif status == 0 and self.PLAYSTATUS == 0:
			self.pseBox.remove(self.pseImg)
			self.pseBox.add(self.plyImg)
			self.PLAYSTATUS = 1

	#
	#  Seeks to an absolute percent in the current target.
	#
	def seekPercent(self, widget, event):

		x, y = event.get_coords()  #resolve desired percent
		percent = 100 * x / PROG_WIDTH

		self.pymp.mplayer.seek(percent, 1)

		if self.pymp.mplayer.mplayerIn:  #little cheat
			self.setProgress(int(percent))

		return True

	#
	#  Sets progBar's fraction and text to percent.  -1 to clear.
	#
	def setProgress(self, percent=-1, time=-1):

		if percent == -1:  #clear bar, return
			self.progBar.set_fraction(0)
			self.progBar.set_text("")
			return

		self.progBar.set_fraction(percent / 100.0)

		if time > -1:  #use time for mplayers that support it
			minutes, seconds = int(time / 60), int(time % 60)
			self.progBar.set_text("%d:%02d" % (minutes, seconds))
		else:  #or fall back on percent for old mplayers
			self.progBar.set_text(str(percent) + "%")

	#
	#  Add targets from a drag and drop event to playlist.
	#  The playlist is first cleared.
	#
	def dragReceived(self, view, context, x, y, data, info, t):

		playlist = self.pymp.playlist

		playlist.clear()
		playlist.dragReceived(view, context, x, y, data, info, t)

		if playlist.continuous:  #and begin playback
			return playlist.jump(0)

		return True

#End of file
