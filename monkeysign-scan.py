#!/usr/bin/env python

import sys, os, stat, gobject, subprocess
import gtk, pygtk; pygtk.require('2.0')
import pango
import re
import tempfile, shutil

from pyme import callbacks, core, errors
from pyme.core import Data, Context, pubkey_algo_name
from pyme import constants
from pyme.constants import validity, protocol
from pyme.constants.keylist import mode

import Image, StringIO
import zbar, zbarpygtk

# threads *must* be properly initialized to use zbarpygtk
gtk.gdk.threads_init()
gtk.gdk.threads_enter()

class MonkeysignScan(gtk.Window):

	ui = '''<ui>
	<menubar name="MenuBar">
		<menu action="File">
			<menuitem action="Quit"/>
		</menu>
	</menubar>
	</ui>'''

	# Keyserver to use
	keyserver = "pool.sks-keyservers.net"

	# Create tempdir for gpg operations
	tempdir = tempfile.mkdtemp(prefix="monkeysign-")

	def __init__(self):
		super(MonkeysignScan, self).__init__()

		# Set up main window
		self.set_title("Monkeysign (scan)")
		self.set_position(gtk.WIN_POS_CENTER)
		self.connect("destroy", self.destroy)

		# Menu
		uimanager = gtk.UIManager()
		accelgroup = uimanager.get_accel_group()
		self.add_accel_group(accelgroup)
		actiongroup = gtk.ActionGroup('MonkeysignGen_Menu')
		actiongroup.add_actions([
															('File', None, '_File'),
															('Quit', gtk.STOCK_QUIT, '_Quit', None, None, self.destroy),
														])
		uimanager.insert_action_group(actiongroup, 0)
		uimanager.add_ui_from_string(self.ui)
		menubar = uimanager.get_widget('/MenuBar')

		# Video device list combo box
		video_found = False
		cell = gtk.CellRendererText()
		cell.props.ellipsize = pango.ELLIPSIZE_END
		self.video_ls = gtk.ListStore(str)
		self.video_cb = gtk.ComboBox(self.video_ls)
		self.video_cb.pack_start(cell, True)
		self.video_cb.add_attribute(cell, 'text', 0)
		for (root, dirs, files) in os.walk("/dev"):
				for dev in files:
						path = os.path.join(root, dev)
						if not os.access(path, os.F_OK):
							continue
						info = os.stat(path)
						if stat.S_ISCHR(info.st_mode) and os.major(info.st_rdev) == 81:
							video_found = True
							self.video_ls.append([path])
		self.video_cb.connect("changed", self.video_changed)

		# Webcam preview display
		if video_found == True:
			self.zbar = zbarpygtk.Gtk()
			self.zbar.connect("decoded-text", self.decoded)
			self.zbarframe = gtk.Frame()
			self.zbarframe.add(self.zbar)
			self.video_cb.set_active(0)
		else:
			camframe = gtk.Frame()
			error_icon = gtk.Image()
			error_icon.set_from_stock(gtk.STOCK_DIALOG_ERROR, gtk.ICON_SIZE_DIALOG)
			vbox = gtk.VBox()
			error_icon_bottom = gtk.Alignment(0, 1, 1, 0)
			error_icon_bottom.add(error_icon)
			error_label_top = gtk.Alignment(0, 0, 1, 0)
			error_label_top.add(gtk.Label("No video device detected."))
			vbox.pack_start(error_icon_bottom)
			vbox.pack_start(error_label_top)
			vbox.set_size_request(320, 320)
			camframe.add(vbox)

		# Setup window layout
		mainvbox = gtk.VBox()
		mainhbox = gtk.HBox()
		lvbox = gtk.VBox()
		lvbox.pack_start(self.video_cb, False, False)
		lvbox.pack_start(self.zbarframe, False, False, 5)
		mainhbox.pack_start(lvbox, False, False, 10)
		mainvbox.pack_start(menubar, False, False)
		mainvbox.pack_start(mainhbox, False, False, 10)
		self.add(mainvbox)

		# Start the show
		self.show_all()

	def video_changed(self, widget=None):
		"""callback invoked when a new video device is selected from the
		drop-down list.  sets the new device for the zbar widget,
		which will eventually cause it to be opened and enabled
		"""
		i = self.video_cb.get_active_iter()
		if i:
			dev = self.video_cb.get_model().get_value(i, 0)
			self.zbar.set_video_device(dev)
		else:
			self.zbar.set_video_enabled(False)

	def decoded(self, zbar, data):
		"""callback invoked when a barcode is decoded by the zbar widget.
		checks for an openpgp fingerprint
		"""

		def update_progress_callback(*args):
			"""callback invoked for pulsating progressbar
			"""
			if self.keep_pulsing:
				self.progressbar.pulse()
				return True
			else:
				return False

		def watch_out_callback(pid, condition):
			"""callback invoked when gpg key download is finished
			"""
			self.keep_pulsing=False
			self.dialog.destroy()
			if condition == 0:
				command = ["/usr/bin/gpg", '--homedir', self.tempdir, '--with-colons', '--list-keys', fpr]
				proc = subprocess.Popen(command, stdout=subprocess.PIPE)
				(stdout, stderr) = proc.communicate()
				stdout = stdout.split("\n")
				for line in stdout:
					if line.startswith("pub"):
						uid = line.split(":")[9]
						md = gtk.MessageDialog(self, gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_QUESTION, gtk.BUTTONS_YES_NO, "Would you like to certify this key/userid pair ?\n\nFingerprint : " + fpr + "\nOwner : " + uid)
						gtk.gdk.threads_enter()
						md.run()
						gtk.gdk.threads_leave()
						md.destroy()
			else:
				md = gtk.MessageDialog(self, gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_ERROR, gtk.BUTTONS_CLOSE, "Key not found.")
				gtk.gdk.threads_enter()
				md.run()
				gtk.gdk.threads_leave()
				md.destroy()
			return

		# Look for prefix and hexadecimal 40-ascii-character fingerprint
		m = re.search("OPENPGP4FPR:([0-9A-F]{40})", data)

		if m != None:
			# Found fingerprint
			fpr = m.group(1)

			# Capture and display the video frame containing QR code
			self.zbarframe.set_shadow_type(gtk.SHADOW_NONE)
			alloc = self.zbarframe.allocation
			pixbuf = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, True, 8, alloc.width, alloc.height)
			pixbuf.get_from_drawable(self.zbarframe.window, self.zbarframe.window.get_colormap(),	alloc.x, alloc.y, 0, 0, alloc.width, alloc.height)
			self.capture = gtk.Image()
			self.capture.set_from_pixbuf(pixbuf)
			self.capture.show()
			self.zbarframe.remove(self.zbar)
			self.zbarframe.add(self.capture)
			self.zbarframe.set_shadow_type(gtk.SHADOW_ETCHED_IN)

			# Disable video capture
			self.zbar.set_video_enabled(False)
			command = ["/usr/bin/gpg", '--homedir', self.tempdir, '--keyserver', self.keyserver, '--recv-keys', fpr]
			self.dialog = gtk.Dialog(title="Please wait", parent=None, flags=gtk.DIALOG_MODAL, buttons=None)
			self.dialog.add_button('gtk-cancel', gtk.RESPONSE_CANCEL)
			message = gtk.Label("Retrieving public key from server...")
			message.show()
			self.progressbar = gtk.ProgressBar()
			self.progressbar.show()
			self.dialog.vbox.pack_start(message, True, True, 5)
			self.dialog.vbox.pack_start(self.progressbar, False, False, 5)
			self.dialog.set_size_request(250, 100)
			self.keep_pulsing = True
			proc = subprocess.Popen(command)
			gobject.child_watch_add(proc.pid, watch_out_callback)
			gobject.timeout_add(100, update_progress_callback)
			if self.dialog.run() == gtk.RESPONSE_CANCEL:
				proc.kill()
			return

	def destroy(self, widget, data=None):
		self.zbar.set_video_enabled(False)
		shutil.rmtree(self.tempdir)
		gtk.main_quit()

	def main(self):
		gtk.main()

MonkeysignScan()
gtk.main()
gtk.gdk.threads_leave()
