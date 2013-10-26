#!/usr/bin/env python

import os, pygtk, gtk, webbrowser

import playlist

EDIT_WIDTH, EDIT_HEIGHT = 300, 200
MPLAYERCONFFILE = os.path.expanduser("~/.pymp/mplayer")

#
#  Provides a standard menu for open, save, help, etc..
#  Main widget: menubar
#
class Menu:

	pymp, popup, path, sorts, sort = None, None, None, None, 0

	#
	#  Creates the menu and adds it to the provided treeview.
	#
	def __init__(self, pymp):

		self.pymp = pymp
		self.path = pymp.prefs.get("path")
		self.sort = pymp.prefs.getInt("sort")

		menuDef = """
		<ui>
			<popup>
				<menu action="File">
					<menuitem action="Open File"/>
					<menuitem action="Open Location"/>
					<menuitem action="Save List"/>
					<menuitem action="Clear List"/>
					<separator/>
					<menuitem action="Quit"/>
				</menu>
				<menu action="Options">
					<menuitem action="Continuous Play"/>
					<menuitem action="Random Play"/>
					<menuitem action="Repeat List"/>
					<menuitem action="Edit MPlayer Config"/>
				</menu>
				<menu action="Sort">
					<menuitem action="By Title"/>
					<menuitem action="By Full Path"/>
					<menuitem action="By Created"/>
					<menuitem action="By Accessed"/>
					<menuitem action="By Added"/>
				</menu>
				<menu action="Help">
					<menuitem action="About"/>
				</menu>
			</popup>
		</ui>
		"""

		uiManager = gtk.UIManager()
		uiManager.add_ui_from_string(menuDef)

		actionGroup = gtk.ActionGroup("Actions")
		actions = (
			("File", None, "_File"),
			("Open File", gtk.STOCK_OPEN, "_Open File", None , None, self.openFile),
			("Open Location", gtk.STOCK_CONVERT, "Open _Location", "<Ctrl>L", None, self.openLocation),
			("Save List", gtk.STOCK_SAVE, "_Save List", None , None, self.saveList),
			("Clear List", gtk.STOCK_CANCEL, "_Clear List", None, None, self.clearList),
			("Options", None, "_Options"),
			("Edit MPlayer Config", gtk.STOCK_PROPERTIES, "_Edit MPlayer Config", None, None, self.editConfig),
			("Sort", None, "_Sort"),
			("Quit", gtk.STOCK_QUIT, "_Quit", None, None, pymp.quit),
			("Help", None, "_Help"),
			("About", gtk.STOCK_HELP, "About", None, None, self.openAbout),
		)
		actionGroup.add_actions(actions)

		cont = gtk.ToggleAction("Continuous Play", "_Continuous Play", None, None)
		cont.connect("toggled", self.toggleContinuous)
		cont.set_active(self.pymp.playlist.continuous)
		actionGroup.add_action(cont)

		rand = gtk.ToggleAction("Random Play", "_Random Play", None, None)
		rand.connect("toggled", self.toggleRandom)
		rand.set_active(self.pymp.playlist.random)
		actionGroup.add_action(rand)

		rep = gtk.ToggleAction("Repeat List", "Repeat _List", None, None)
		rep.connect("toggled", self.toggleRepeat)
		rep.set_active(self.pymp.playlist.repeat)
		actionGroup.add_action(rep)

		self.sorts = [
			("By Title", None, "By _Title", None, None, playlist.COL_TITLE),
			("By Full Path", None,"By _Full Path", None, None, playlist.COL_TARGET),
			("By Created", None, "By _Created", None, None, playlist.COL_CTIME),
			("By Accessed", None, "By _Accessed", None, None, playlist.COL_ATIME),
			("By Added", None, "By _Added", None, None, playlist.COL_TID)
		]

		actionGroup.add_radio_actions(self.sorts, self.sort, self.sortList)

		model = self.pymp.playlist.view.get_model()
		model.set_sort_column_id(self.sort, gtk.SORT_ASCENDING)

		uiManager.insert_action_group(actionGroup, 0)

		popup = uiManager.get_widget("/popup")

		self.pymp.window.add_accel_group(uiManager.get_accel_group())

		self.popup = popup

	#
	#  Displays a dialog to open a location.
	#
	def openLocation(self, widget, data=None):

		flags = gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT

		buttons = (  #define okay and cancel buttons
			gtk.STOCK_OK, gtk.RESPONSE_ACCEPT,
			gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT
		)

		entry = gtk.Entry(255)  #create text entry field
		entry.set_activates_default(True)
		entry.set_width_chars(40)
		entry.show()

		dialog = gtk.Dialog("Open Location...", self.pymp.window, flags, buttons)
		dialog.set_default_response(gtk.RESPONSE_ACCEPT)

		dialog.vbox.pack_start(entry, False, True, 0)

		if dialog.run() == gtk.RESPONSE_ACCEPT:  #process location
			self.pymp.playlist.load([entry.get_text()])

		dialog.destroy()
		return True

	#
	#  Displays a file chooser dialog to add files to playlist.
	#
	def openFile(self, widget, data=None):

		SELECT_ALL = 1234
		ADD = 0
		buttons = (  #define open and cancel buttons
			"Select All", SELECT_ALL,
			"Add", ADD,
			gtk.STOCK_OPEN, gtk.RESPONSE_ACCEPT,
			gtk.STOCK_CANCEL, gtk.RESPONSE_CLOSE
		)

		fileChooser = gtk.FileChooserDialog(self.pymp.versionString,
			self.pymp.window, 0, buttons)  #create chooser

		fileChooser.set_default_response(gtk.RESPONSE_ACCEPT)
		fileChooser.set_current_folder(self.path)
		fileChooser.set_select_multiple(True)

		while True:

			response = fileChooser.run()

			if response == SELECT_ALL:  #select all and continune
				fileChooser.select_all()
				continue

			if response == gtk.RESPONSE_ACCEPT:  #process selected files

				self.pymp.playlist.load(fileChooser.get_filenames())
				self.path = fileChooser.get_current_folder()

			if response == ADD: #We can add songs without closing

				for f in fileChooser.get_filenames():  #load files or lists
					self.pymp.playlist.add(f)

				self.path = fileChooser.get_current_folder()
				continue

			break  #break from loop

		fileChooser.destroy()  #dispose of chooser
		return True

	#
	#  Saves the current playlist to the specified file.
	#
	def saveList(self, widget, data=None):

		buttons = (  #define save and cancel buttons
			gtk.STOCK_SAVE, gtk.RESPONSE_ACCEPT,
			gtk.STOCK_CANCEL, gtk.RESPONSE_CLOSE
		)

		fileChooser = gtk.FileChooserDialog(self.pymp.versionString, self.pymp.window,
			gtk.FILE_CHOOSER_ACTION_SAVE, buttons)  #create chooser

		fileChooser.set_default_response(gtk.RESPONSE_ACCEPT)
		fileChooser.set_current_folder(self.path)
		fileChooser.set_current_name(".m3u")

		if fileChooser.run() == gtk.RESPONSE_ACCEPT:  #save list

			self.pymp.playlist.save(fileChooser.get_filename())

			self.path = fileChooser.get_current_folder()

		fileChooser.destroy()  #dispose of chooser
		return True

	#
	#  Clears the current playlist.
	#
	def clearList(self, widget, data=None):
		self.pymp.playlist.clear()
		return True

	#
	#  Assigns the appropriate sorting function for the playlist.
	#
	def sortList(self, widget, current, data=None):

		model = self.pymp.playlist.view.get_model()
		col = widget.get_current_value()

		model.set_sort_column_id(col, gtk.SORT_ASCENDING)
		model.sort_column_changed()

		pl = self.pymp.playlist

		if pl.current:  #scroll to current, may have moved offscreen
			pl.view.scroll_to_cell(pl.path())

		self.sort = col
		return True

	#
	#  Sets the continuous playback option from a toggle item.
	#
	def toggleContinuous(self, widget):
		self.pymp.playlist.continuous = widget.get_active()
		return True

	#
	#  Sets the random playback option from a toggle item.
	#
	def toggleRandom(self, widget):
		self.pymp.playlist.random = widget.get_active()
		return True

	#
	#  Sets the reapeat option from a toggle item.
	#
	def toggleRepeat(self, widget):
		self.pymp.playlist.repeat = widget.get_active()
		return True

	#
	#  Opens ~/.mplayer/config and allows editing.
	#
	def editConfig(self, widget):

		flags = gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT

		buttons = (  #define okay and cancel buttons
			gtk.STOCK_OK, gtk.RESPONSE_ACCEPT,
			gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT
		)

		buff = gtk.TextBuffer()  #create text entry field

		if os.path.isfile(MPLAYERCONFFILE):
			config = open(MPLAYERCONFFILE)
			buff.set_text(config.read())
			config.close()

		view = gtk.TextView(buff)
		view.set_size_request(EDIT_WIDTH, EDIT_HEIGHT)
		view.show()

		dialog = gtk.Dialog("Edit MPlayer Config...", self.pymp.window, flags, buttons)
		dialog.set_default_response(gtk.RESPONSE_ACCEPT)

		dialog.vbox.pack_start(view, True, True, 0)

		if dialog.run() == gtk.RESPONSE_ACCEPT:  #overwrite config

			config = open(MPLAYERCONFFILE, "w")

			start, end = buff.get_start_iter(), buff.get_end_iter()
			config.write(buff.get_text(start, end))

			config.close()

		dialog.destroy()
		return True

	#
	#  Attempts to visit the Pymp homepage in a new browser tab.
	#
	def openHomepage(self, dialog, link, data=None):
		webbrowser.open(link, 2, 1)

	#
	#  Displays an AboutDialog for the application.
	#
	def openAbout(self, widget, data=None):

		gtk.about_dialog_set_url_hook(self.openHomepage)

		about = gtk.AboutDialog()

		about.set_name("")
		about.set_version(self.pymp.versionString)

		about.set_authors(["Jay Dolan <jdolan@jdolan.dyndns.org>",
				"Lucas Hazel <lucas@die.net.au>",
				"Brian Miculcy <morlenxus@gmx.net>"])

		about.set_artists(["Jay Dolan <jdolan@jdolan.dyndns.org>"])

		about.set_website("http://jdolan.dyndns.org/pymp")

		about.set_logo(self.pymp.getIcon())

		about.show()
		about.run()
		about.hide()
		about.destroy()
		return True

#End of file
