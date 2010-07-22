#!/usr/bin/env python

import pygtk; pygtk.require('2.0')
import gtk
import pango

from pyme import callbacks, core, errors
from pyme.core import Data, Context, pubkey_algo_name
from pyme import constants
from pyme.constants import validity, protocol
from pyme.constants.keylist import mode

import Image, StringIO
from qrencode import encode as _qrencode
from qrencode import encode_scaled as _qrencode_scaled

class MonkeysignGen(gtk.Window):

	ui = '''<ui>
	<menubar name="MenuBar">
		<menu action="File">
			<menuitem action="Save as..."/>
			<separator name="FileSeparator1"/>
			<menuitem action="Quit"/>
		</menu>
	</menubar>
	</ui>'''

	def __init__(self):
		super(MonkeysignGen, self).__init__()

		self.ultimate_keys = self.list_ultimate_keys()
		self.last_allocation = gtk.gdk.Rectangle()

		# Set up main window
		self.set_title("Monkeysign (generate)")
		self.set_position(gtk.WIN_POS_CENTER)
		self.set_default_size(350,460)
		self.connect("destroy", gtk.main_quit)
		self.connect("expose-event", self.expose_event)

		# Menu
		uimanager = gtk.UIManager()
		accelgroup = uimanager.get_accel_group()
		self.add_accel_group(accelgroup)
		actiongroup = gtk.ActionGroup('MonkeysignGen_Menu')
		actiongroup.add_actions([
															('File', None, '_File'),
															('Save as...', gtk.STOCK_SAVE, '_Save as...', 'S', None, self.save_qrcode),
															('Quit', gtk.STOCK_QUIT, '_Quit', 'Q', None, self.destroy),
														])
		uimanager.insert_action_group(actiongroup, 0)
		uimanager.add_ui_from_string(self.ui)
		menubar = uimanager.get_widget('/MenuBar')

		# Ultimate keys list
		cell = gtk.CellRendererText()
		cell.props.ellipsize = pango.ELLIPSIZE_END
		self.ls = gtk.ListStore(str, str)
		self.cb = gtk.ComboBox(self.ls)
		self.cb.pack_start(cell, True)
		self.cb.add_attribute(cell, 'text', 0)
		for key in self.ultimate_keys:
			keytext = key.subkeys[0].keyid[8:] + ':'
			if key.uids[0].name:
				keytext += ' ' + key.uids[0].name
			if key.uids[0].comment:
				keytext += ' (' + key.uids[0].comment + ')'
			if key.uids[0].email:
				keytext += ' <' + key.uids[0].email + '>'
			self.ls.append([keytext,key.subkeys[0].fpr])
		self.cb.connect("changed", self.key_changed)

		# QR Code widget
		self.qrcode = gtk.Image()

		# Save button
		save = gtk.Button(stock=gtk.STOCK_SAVE)
		save.connect("clicked", self.save_qrcode);

		# Setup window layout
		mainvbox = gtk.VBox()
		hbox = gtk.HBox(False, 2)
		vbox = gtk.VBox(False, 2)
		vbox.pack_start(self.cb, False, False, 3)
		self.swin = gtk.ScrolledWindow()
		self.swin.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
		self.swin.add_with_viewport(self.qrcode)
		vbox.pack_start(self.swin, True, True, 0)
		halign = gtk.Alignment(0.5, 0, 0, 0)
		halign.add(save)
		vbox.pack_start(halign, False, False, 3)
		hbox.pack_start(vbox, True, True, 10)
		mainvbox.pack_start(menubar, False)
		mainvbox.pack_start(hbox, True, True, 10)
		self.add(mainvbox)

		# Start the show
		self.show_all()
		self.last_allocation = self.get_allocation()

		# Select first key
		self.cb.set_active(0)

	def expose_event(self, widget, event):
		"""When window is resized, regenerate the QR code"""
		if self.get_allocation() != self.last_allocation:
			self.last_allocation = self.get_allocation()
			self.key_changed(self.cb)

	def key_changed(self, widget):
		"""When another key is chosen, generate new QR code"""
		i = widget.get_active_iter()
		fpr = self.cb.get_model().get_value(i, 1)
		pixbuf = self.image_to_pixbuf(self.make_qrcode(fpr))
		self.qrcode.set_from_pixbuf(pixbuf)

	def list_ultimate_keys(self):
		"""Retrieve list of keys for which the user might want a QR code"""
		keys = []
		c = core.Context()
		c.set_protocol(protocol.OpenPGP)
		c.set_keylist_mode(mode.LOCAL)
		for key in c.op_keylist_all(None, False):
			if key.owner_trust == validity.ULTIMATE:
				keys.append(key)
		return keys

	def make_qrcode(self, fingerprint):
		"""Given a fingerprint, generate a QR code with appropriate prefix"""
		rect = self.swin.get_allocation()
		if rect.width < rect.height:
			size = rect.width - 15
		else:
			size = rect.height - 15
		version, width, image = _qrencode_scaled('openpgp4fpr:'+fingerprint,size,0,1,2,True)
		return image

	def save_qrcode(self, widget=None):
		"""Use a file chooser dialog to enable user to save the current QR code as a PNG image file"""
		key = self.ultimate_keys[self.cb.get_active()]
		image = self.make_qrcode(key.subkeys[0].fpr)
		dialog = gtk.FileChooserDialog("Save QR code", None, gtk.FILE_CHOOSER_ACTION_SAVE, (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_SAVE, gtk.RESPONSE_OK))
		dialog.set_default_response(gtk.RESPONSE_OK)
		dialog.set_current_name(key.subkeys[0].keyid[8:] + '.png')
		dialog.show()
		response = dialog.run()
		if response == gtk.RESPONSE_OK:
				name = dialog.get_filename()
				image.save(name, 'PNG')
		elif response == gtk.RESPONSE_CANCEL:
				pass
		dialog.destroy()
		return

	def image_to_pixbuf(self, image):
		"""Utility function to convert a PIL image instance to Pixbuf"""
		fd = StringIO.StringIO()
		image.save(fd, "ppm")
		contents = fd.getvalue()
		fd.close()
		loader = gtk.gdk.PixbufLoader("pnm")
		loader.write(contents, len(contents))
		pixbuf = loader.get_pixbuf()
		loader.close()
		return pixbuf

	def destroy(self, widget, data=None):
		gtk.main_quit()

	def main(self):
		gtk.main()

MonkeysignGen()
gtk.main()
