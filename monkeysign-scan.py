#!/usr/bin/env python

import subprocess
import pygtk; pygtk.require('2.0')
import gtk

from pyme import callbacks, core, errors
from pyme.core import Data, Context, pubkey_algo_name
from pyme import constants
from pyme.constants import validity, protocol
from pyme.constants.keylist import mode

import Image, StringIO
import zbar

class MonkeysignScan(gtk.Window):

	def __init__(self):
		super(MonkeysignScan, self).__init__()

		# Set up main window
		self.set_title("Monkeysign (scan)")
		self.set_position(gtk.WIN_POS_CENTER)
		self.set_default_size(350,400)
		self.set_border_width(10)
		self.connect("destroy", gtk.main_quit)

		# QR code thumbnail
		self.thumbnail = gtk.Image()

		# Import button
		importimg = gtk.Button("Import image")
		importimg.connect("clicked", self.import_image)

		# Detected keys list
		self.ls = gtk.ListStore(str)
		self.treeview = gtk.TreeView(self.ls)
		self.treeview.set_rules_hint(True)
		cell = gtk.CellRendererText()
		column = gtk.TreeViewColumn("Fingerprint", cell, text=0)
		self.treeview.append_column(column)

		# Retrieve keys button
		self.retrieve = gtk.Button("Retrieve keys")
		self.retrieve.connect("clicked", self.retrieve_keys_btn);

		# Close button
		close = gtk.Button(stock=gtk.STOCK_CLOSE)
		close.connect("clicked", self.destroy);

		# Setup window layout
		vbox = gtk.VBox(False, 5)
		vbox.pack_start(self.thumbnail, False, False, 3)
		halign1 = gtk.Alignment(0.5, 0, 0, 0)
		halign1.add(importimg)
		vbox.pack_start(halign1, False, False, 3)
		vbox.pack_start(self.treeview, False, False, 3)
		halign2 = gtk.Alignment(0.5, 0, 0, 0)
		halign2.add(self.retrieve)
		vbox.pack_start(halign2, False, False, 3)
		halign3 = gtk.Alignment(0.5, 0, 0, 0)
		halign3.add(close)
		vbox.pack_start(halign3, False, False, 3)
		self.add(vbox)

		importimg.show()
		close.show()
		halign1.show()
		halign2.show()
		halign3.show()
		vbox.show()
		self.show()

	def import_image(self, widget):
		"""Use a file chooser dialog to import an image containing a QR code"""
		dialog = gtk.FileChooserDialog("Open QR code image", None, gtk.FILE_CHOOSER_ACTION_OPEN, (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK))
		dialog.set_default_response(gtk.RESPONSE_OK)
		dialog.show()
		response = dialog.run()
		if response == gtk.RESPONSE_OK:
				self.filename = dialog.get_filename()
				self.image = Image.open(self.filename)
				pixbuf = gtk.gdk.pixbuf_new_from_file(self.filename)
				self.thumbnail.set_from_pixbuf(self.scale_pixbuf(pixbuf))
				self.thumbnail.show()
				self.scan_image()
		elif response == gtk.RESPONSE_CANCEL:
				pass
		dialog.destroy()
		return

	def scale_ratio(self, src_width, src_height, dest_width, dest_height):
		"""Return a size fitting into dest preserving src's aspect ratio."""
		if src_height > dest_height:
			if src_width > dest_width:
				ratio = min(float(dest_width) / src_width, float(dest_height) / src_height)
			else:
				ratio = float(dest_height) / src_height
		elif src_width > dest_width:
				ratio = float(dest_width) / src_width
		else:
				ratio = 1
		return int(ratio * src_width), int(ratio * src_height)

	def scale_pixbuf(self, pixbuf):
		"""Scale pixbuf according to window size"""
		allocation = self.get_allocation()
		target_width, target_height = self.scale_ratio(pixbuf.get_width(), pixbuf.get_height(), allocation.width, allocation.height)
		pixbuf = pixbuf.scale_simple(target_width, target_height, gtk.gdk.INTERP_HYPER)
		return pixbuf

	def scan_image(self):
		"""Scan an image for QR codes"""
		# create a reader
		scanner = zbar.ImageScanner()

		# configure the reader
		scanner.parse_config('enable')

		# obtain image data
		pil = self.image.convert('L')
		width, height = pil.size
		raw = pil.tostring()

		# wrap image data
		image = zbar.Image(width, height, 'Y800', raw)

		# scan the image for barcodes
		scanner.scan(image)

		# extract results
		for symbol in image:
			if symbol.data.startswith('openpgp4fpr:'):
				fpr = symbol.data.split(':')[1]
				# Add to treeview if not already there
				try: (f for f in self.get_fpr_list() if fpr in f).next()
				except StopIteration:
					self.ls.append([fpr])
					# Activate treeview and retrieve key button
					if self.treeview.flags() ^ gtk.VISIBLE:
						self.treeview.show()
					if self.retrieve.flags() ^ gtk.VISIBLE:
						self.retrieve.show()

		# clean up
		del(image)

	def get_fpr_list(self):
		"""Extract a list of fingerprints from the treeview component"""
		fpr = []
		i = self.treeview.get_model().get_iter_first()
		if i:
			fpr.append(self.treeview.get_model().get_value(i,0))
			while self.treeview.get_model().iter_next(i):
				i = self.treeview.get_model().iter_next(i)
				fpr.append(self.treeview.get_model().get_value(i,0))
		return fpr

	def retrieve_keys_btn(self, widget):
		"""Wrapper for button"""
		self.retrieve_keys()
		return

	def retrieve_keys(self):
		"""Retrieve detected keys and add them to local keyring"""
		for fpr in self.get_fpr_list():
			havekey = False
			c = core.Context()
			c.set_protocol(protocol.OpenPGP)
			c.set_keylist_mode(mode.LOCAL)
			# Check if we don't have it already
			for key in c.op_keylist_all(fpr, False):
				havekey = True
				print "Already have that key."
			if havekey == False:
				# PyMe doesn't seem to support fetching keys from a keyserver...
				retcode = subprocess.call(["/usr/bin/gpg", '--keyserver', 'pool.sks-keyservers.net', '--recv-keys', fpr])
				if retcode == 0:
					print "Success!"
		return

	def destroy(self, widget, data=None):
		gtk.main_quit()

	def main(self):
		gtk.main()

MonkeysignScan()
gtk.main()
