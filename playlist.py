#!/usr/bin/env python

import os, gobject, pango, pygtk, gtk, random, urllib

import mplayer

PLAYLIST = os.path.expanduser("~/.pymp/playlist")

MIN_WIDTH, MIN_HEIGHT, SCROLL_STEP, TIP_TIMEOUT = 250, 38, 20, 1200

COL_TID, COL_TARGET, COL_CTIME, COL_ATIME = 0, 1, 2, 3
COL_TITLE, COL_WEIGHT, COL_WEIGHT_SET = 4, 5, 6

#
#  Compare two treestore rows, used for sorting.
#
def compare(model, iter1, iter2, data=None):

	(c, order) = model.get_sort_column_id()
	if c < 0:
		return 0

	x = model.get_value(iter1, c)
	y = model.get_value(iter2, c)

	if x < y:
		return -1
	if x == y:
		return 0
	return 1

#
#  Provides a playlist store to queue mplayer jobs.
#  Main widget: view
#
class Playlist:

	pymp, view, current, counter, history, randomlist = None, None, None, 1, [], []
	continuous, random, repeat = True, False, False
	loadcount, loadcur = 0, 0

	#
	#  Creates the playlist widgets and adds them to vbox.
	#
	def __init__(self, pymp):

		self.pymp = pymp

		self.continuous = pymp.prefs.getBool("continuous")
		self.random = pymp.prefs.getBool("random")
		self.repeat = pymp.prefs.getBool("repeat")

		#tid, target, ctime, atime, title, font weight, weight set
		model = gtk.ListStore(int, str, int, int, str, int, bool)

		model.set_sort_func(COL_TARGET, compare)
		model.set_sort_func(COL_CTIME, compare)
		model.set_sort_func(COL_ATIME, compare)
		model.set_sort_func(COL_TITLE, compare)

		renderer = gtk.CellRendererText()
		column = gtk.TreeViewColumn(None, renderer,  #initialize display column
			text=COL_TITLE, weight=COL_WEIGHT, weight_set=COL_WEIGHT_SET)

		view = gtk.TreeView(model)
		view.append_column(column)
		view.set_enable_search(True)
		view.set_search_column(COL_TITLE)
		view.set_search_equal_func(self.search, None)

		view.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
		view.set_size_request(MIN_WIDTH, MIN_HEIGHT)
		view.set_headers_visible(False)

		target = [("text/uri-list", 0, 0)]  #external drag/drop
		view.drag_dest_set(gtk.DEST_DEFAULT_ALL, target, gtk.gdk.ACTION_COPY)
		view.connect("drag-data-received", self.dragReceived)


		view.connect("button-press-event", self.menu)
		view.connect("row-activated", self.activate)
		view.connect("key-press-event", self.key)
		view.connect("scroll-event", self.scroll)

		font = pango.FontDescription("8")
		view.modify_font(font)

		self.view = view

		scrollview = gtk.ScrolledWindow()
		scrollview.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
		scrollview.add(view)

		self.scrollview = scrollview


	#
	#  Displays the main popup menu on a button-press-event.
	#
	def menu(self, widget, event):

		if event.button != 3:  #only on right click
			return False

		menu, time = self.pymp.menu, event.get_time()
		menu.popup.popup(None, None, None, 3, time)
		return True

	#
	# Sets the title of a track and the window title
	#
	def set_track_title(self, title):

		self.pymp.playlist.view.get_model().set(self.pymp.playlist.it, COL_TITLE, title)
		self.pymp.window.set_title(title)

	#  Returns the current path of target by tid, or None if such a target is no longer in list.
	#  As a convenience, if tid is None, self.current will be tried in it's place.
	#
	def path(self, tid=None):

		if not tid:  #no param passed
			tid = self.current

			if not tid:  #self.current not yet set
				return None

		model = self.view.get_model()
		it = model.get_iter_first()

		while it:
			if model.get_value(it, COL_TID) == tid:
				return model.get_path(it)
			it = model.iter_next(it)

		return None

	#
	#  Plays the specified target from the playlist.
	#
	def play(self, path, log=True, event=None):

		if self.current:  #stop if necessary
			self.stop(None, None)

		if log and self.current:  #append current target to history
			self.history.append(self.current)

		self.it = self.view.get_model().get_iter(path)
		tid = self.view.get_model().get_value(self.it, COL_TID)
		target = self.view.get_model().get_value(self.it, COL_TARGET)
		title = self.view.get_model().get_value(self.it, COL_TITLE)

		self.view.get_model().set(self.it, COL_WEIGHT_SET, True)  #bold target
		self.view.scroll_to_cell(path)  #show target

		if event:  #clear selection, select target, show info
			self.view.get_selection().unselect_all()
			self.view.get_selection().select_path(path)

		self.current = tid  #note target

		self.pymp.mplayer.play(target)  #begin playing target
		self.pymp.window.set_title(title)
		return True

	#
	#  Plays a target step rows from the currently active target.
	#
	def jump(self, step, log=True, event=None):

		if not len(self.view.get_model()):  #empty list
			return True

		self.view.get_selection().unselect_all()  #unselect anything selected
		model = self.view.get_model()

		if not self.current:  #jump from beginning
			it = model.get_iter_first()
		else:
			it = model.get_iter(self.path())
		# assign it, if not it crashes because wasn't assigned
		# may be it needs to be fixed better
		# ind = int(model.get_string_from_iter(it))
		if self.random:  #disregard step, use random
			step = random.randint(1, len(model))
			ind = int(model.get_string_from_iter(it))
			ind = (ind + step) % len(model)
			while ind in self.randomlist: #check if was played
				step = random.randint(1, len(model))
				ind = int(model.get_string_from_iter(it))
				ind = (ind + step) % len(model)

			self.randomlist.append(ind) #add it to the random list

			if (len(self.randomlist) == len(model)) and not self.repeat:
				self.randomlist = [] #clean all
				self.current = None
				self.history = []
				try:  #unbold current target in list
					it = self.view.get_model().get_iter(self.path())
					self.view.get_model().set(it, COL_WEIGHT_SET, False)
				except StandardError:
					pass
				return self.stop(None, None)

			if (len(self.randomlist) == len(model)) and self.repeat:
				self.randomlist = [] #clean all
				self.history = []
				if not self.current:  #jump from beginning
					it = model.get_iter_first()
				else:
					it = model.get_iter(self.path())
				ind = int(model.get_string_from_iter(it))
				ind = (ind + step) % len(model)
				it = model.get_iter(str(ind))
				path = model.get_path(it)  #resolve path
				return self.play(path, log, event)

			it = model.get_iter(str(ind))
			path = model.get_path(it)  #resolve path
			return self.play(path, log, event)

		if not self.continuous:
			return self.stop(None, None)

		if self.exhausted() and not self.repeat:
			self.current = None
			self.history = []
			return self.stop(None, None)

		ind = int(model.get_string_from_iter(it))
		ind = (ind + step) % len(model)
		it = model.get_iter(str(ind))

		path = model.get_path(it)  #resolve path
		return self.play(path, log, event)

	#
	#  Stops the current mplayer job and prevents a jump.
	#
	def stop(self, widget, event):

		self.pymp.mplayer.close()

		try:  #unbold current target in list
			it = self.view.get_model().get_iter(self.path())
			self.view.get_model().set(it, COL_WEIGHT_SET, False)
		except StandardError:
			pass

		self.pymp.window.set_title(self.pymp.versionString)
		return True

	#
	#  Returns True if the playlist has been exhausted, False otherwise.
	#
	def exhausted(self):

		if self.repeat:  #never exhausted
			return False

		model = self.view.get_model()
		it = model.get_iter_first()

		while it:  #exhausted if all played

			tid = model.get_value(it, COL_TID)

			if tid not in self.history and tid is not self.current:
				return False

			if self.randomlist:
				if tid not in self.randomlist and tid is not self.current:
					return False

			it = model.iter_next(it)

		return True

	#
	#  Plays the selected file from the playlist.
	#
	def activate(self, view, path, column):
		return self.play(path)

	#
	#  Scrolls the view up or down, depending on event.direction.
	#
	def scroll(self, widget, event):

		x, y, limit = 0, 0, -1 * SCROLL_STEP

		if event.direction == gtk.gdk.SCROLL_DOWN:
			alloc = self.view.get_allocation()
			x, y, limit = alloc.x, alloc.y, SCROLL_STEP

		tx, ty = self.view.widget_to_tree_coords(x, y)
		self.view.scroll_to_point(0, ty + limit)
		return True

	#
	#  Do case insensitive wildcard search on target titles.
	#
	def search(self, model, column, key, it, data):

		key, title = key.lower(), model.get_value(it, column).lower()
		return title.find(key) == -1

	#
	#  Plays a previously played target if available, jumps otherwise.
	#
	def prev(self, widget, event):

		path = None
		while not path and len(self.history):
			path = self.path(self.history.pop())

		if path:  #play target from history
			return self.play(path, False, event)

		return self.jump(-1, False, event)

	#
	#  Plays the next available target.
	#
	def next(self, widget, event):

		if not event and self.exhausted():  #exhausted list, return
			return self.stop(None, None)  #reset window title, etc

		return self.jump(1, True, event)

	#
	#  Handle key events such as Delete, Pause, Prev, and Next.
	#
	def key(self, widget, event):

		string, state = event.string, event.state
		keycode = event.hardware_keycode

		selection = self.view.get_selection()
		model, paths = selection.get_selected_rows()

		if keycode == 107 or keycode == 119:  #delete, remove selected
			self.remove(model, paths)
		elif keycode == 36:  #enter
			if paths: self.play(paths[0])  #play selected
			elif self.current: self.play(self.path())  #or current
			else: self.jump(1)  #or jump, play something
		elif keycode == 100:  #left, seek reverse
			self.pymp.mplayer.seek(-10)
		elif keycode == 102:  #right, seek forward
			self.pymp.mplayer.seek(10)
		elif keycode == 59:  #<, jump previous
			self.prev(None, event)
		elif keycode == 60:  #>, jump next
			self.next(None, event)
		elif keycode == 33 or keycode == 65:  # p or spacebar, pause
			self.pymp.mplayer.pause()
		elif keycode == 39:  #s, stop
			self.stop(None, None)
		elif string is "" or state > 0:  #ignore up, dwn, ctrl-f, etc
			return False

		return True  #mute others

	#
	#  Add targets from a drag and drop event to playlist.
	#
	def dragReceived(self, view, context, x, y, data, info, time):
		self.load(data.data.split("\r\n")[:-1])  #tokenize and load
		return True

	#
	#  Returns the title of the current target, or None.
	#
	def status(self):

		if not self.current:
			return self.pymp.versionString

		model = self.view.get_model()
		it = model.get_iter(self.path())

		return model.get_value(it, COL_TITLE)

	#
	#  Saves playlist to the specified file, defaulting to PLAYLIST.
	#
	def save(self, filename=PLAYLIST):

		try:
			f = open(filename, "w")
		except StandardError:
			return False

		model = self.view.get_model()
		it = model.get_iter_first()

		while it:  #append each target to file
			f.write(model.get_value(it, COL_TARGET) + "\n")
			it = model.iter_next(it)

		f.close()
		return True

	#
	#  Loads the specified .m3u playlist file, defaulting to PLAYLIST.
	#
	def loadm3u(self, filename=PLAYLIST):

		self.loadcur += 1

		try:
			f = open(filename, "r")
		except StandardError:
			return False

		targets = []
		for line in f:
			if not line.startswith("#"):
				targets.append(line.strip())

		f.close()
		self.load(targets)
		return True

	#
	#  Loads the specified .pls playlist file.
	#
	def loadpls(self, filename):

		self.loadcur += 1

		try:
			f = open(filename, "r")
		except StandardError:
			return False

		targets = []
		for line in f:
			if line.startswith("File"):
				targets.append(line.split("=", 1)[1].strip())

		f.close()
		self.load(targets)
		return True

	#
	#  Loads all files in the specified directory.
	#
	def loaddir(self, dirname):

		self.loadcur += 1

		targets = []
		for f in os.listdir(dirname):
			if not f.startswith("."):  #skip dotfiles
				targets.append(dirname + "/" + f)

		self.load(targets)
		return True

	#
	#  Loads the specified targets (lazily) to the playlist.
	#
	def load(self, targets):

		self.loadcount += len(targets)

		for t in targets:
			target = urllib.unquote(t).replace("file://", "")

			if target.endswith(".m3u"):  #load .m3u files
				self.loadm3u(target)

			elif target.endswith(".pls"):  #load .pls files
				self.loadpls(target)

			elif os.path.isdir(target):  #load directories
				self.loaddir(target)

			else:  #load normal files
				gobject.idle_add(self.add, target)

		return True

	#
	#  Adds the specified target to the playlist.
	#
	def add(self, target):

		self.loadcur += 1
		self.counter += 1

		tid = self.counter

		if target.find("://") > -1:  #locations, http://, dvd://
			ctime = atime = 0
			name = target
		else:  #normal files, resolve timestamps, use basename
			st = os.stat(target)
			ctime, atime = st.st_ctime, st.st_atime
			name = os.path.basename(target)

		row = [tid, target, ctime, atime, name, pango.WEIGHT_BOLD, False]
		self.view.get_model().append(row)

		if self.loadcur >= self.loadcount:  #caught up, reorder list
			self.view.get_model().sort_column_changed()
			self.pymp.control.setProgress(-1)
		else:  #update loading progress
			percent = 100 * self.loadcur / self.loadcount
			self.pymp.control.setProgress(percent)

		return False  #cancel idle callback

	#
	#  Removes targets at the specified paths.  Stops playback and
	#  jumps if necessary and appropriate.
	#
	def remove(self, model, paths):

		deletedCurrent = self.path() in paths
		iters = [model.get_iter(p) for p in paths]

		for it in iters:  #remove by iter reference
			model.remove(it)

		if deletedCurrent:  #stop, jump if continuous
			self.stop(None, None)
			self.current = None;

			if self.continuous:
				return self.jump(1)

		return True

	#
	#  Stops playback and removes all targets from playlist.
	#
	def clear(self):

		if self.current:  #stop if necessary
			self.stop(None, None)
			self.current = None
			self.history = []
			self.randomlist = []

		self.view.get_model().clear()
		return True

#End of file
