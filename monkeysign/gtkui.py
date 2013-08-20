# -*- coding: utf-8 -*-
#
#    Copyright (C) 2010 Jerome Charaoui
#    Copyright (C) 2012-2013 Antoine Beaupré <anarcat@orangeseeds.org>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys, os, stat, subprocess
import re
import StringIO
import gtk

import gobject
import pygtk; pygtk.require('2.0')
import pango
import Image # XXX: what *is* this library exactly?!
import zbar, zbarpygtk

from qrencode import encode as _qrencode
from qrencode import encode_scaled as _qrencode_scaled

from monkeysign.gpg import Keyring
from monkeysign.ui import MonkeysignUi
import monkeysign.translation

class MonkeysignScanUi(MonkeysignUi):
        """sign a key in a safe fashion using a webcam to scan for qr-codes

This command will fire up a graphical interface and turn on the webcam
(if available) on this computer. It will also display a qr-code of
your main OpenPGP key.

The webcam is used to capture an OpenPGP fingerprint represented as a
qrcode (or whatever the zbar library can parse) and then go through a
signing process.

The signature is then encrypted and mailed to the user. This leave the
choice of publishing the certification to that person and makes sure
that person owns the identity signed.

This program assumes you have gpg-agent configure to prompt for
passwords.
"""

        def main(self):
                # threads *must* be properly initialized to use zbarpygtk
                gtk.gdk.threads_init()
                gtk.gdk.threads_enter()

                self.window = MonkeysignScan()
                self.window.msui = self

                # XXX: this probably belongs lower in the stack,
                # because we don't want to create a temporary keyring
                # just when we start the graphical UI, but instead
                # really when we sign
                MonkeysignUi.main(self)

                gtk.main()
                gtk.gdk.threads_leave()

        def yes_no(self, prompt, default = None):
                """we ignore default! gotta fix that"""
                md = gtk.MessageDialog(self.window, gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_QUESTION, gtk.BUTTONS_YES_NO, prompt)
                with gtk.gdk.lock:
                        response = md.run()
                md.destroy()
                return response == gtk.RESPONSE_YES

        def abort(self, prompt):
                """we don't actually abort, just exit threads and resume capture"""
                md = gtk.MessageDialog(self.window, gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_ERROR, gtk.BUTTONS_CLOSE, prompt)
                with gtk.gdk.lock:
                        md.run()
                md.destroy()
                self.window.resume_capture()

        def warn(self, prompt):
                """display the message but let things go"""
                md = gtk.MessageDialog(self.window, gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_WARNING, gtk.BUTTONS_OK, prompt)
                with gtk.gdk.lock:
                        md.run()
                md.destroy()

        def choose_uid(self, prompt, key):
                md = gtk.Dialog(prompt, self.window, gtk.DIALOG_DESTROY_WITH_PARENT, (gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT, gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
                # simple explanation
                l = gtk.Label(prompt)
                md.vbox.pack_start(l)
                l.show()
                # list of uids
                self.uid_radios = None
                for uid in key.uidslist:
                        r = gtk.RadioButton(self.uid_radios, uid.uid)
                        r.show()
                        md.vbox.pack_start(r)
                        if self.uid_radios is None:
                                self.uid_radios = r
                                self.uid_radios.set_active(True)

                with gtk.gdk.lock:
                        response = md.run()

                label = None
                if response == gtk.RESPONSE_ACCEPT:
                        self.log(_('okay, signing'))
                        label = [ r for r in self.uid_radios.get_group() if r.get_active()][0].get_label()
                else:
                        self.log(_('user denied signature'))
                md.destroy()
                return label

class MonkeysignScan(gtk.Window):

        ui = '''<ui>
        <menubar name="MenuBar">
                <menu action="File">
                        <menuitem action="Open image..."/>
                        <menuitem action="Save as..."/>
                        <separator name="FileSeparator1"/>
                        <menuitem action="Print"/>
                        <separator name="FileSeparator2"/>
                        <menuitem action="Quit"/>
                </menu>
                <menu action="Edit">
                        <menuitem action="Copy"/>
                </menu>
        </menubar>
        </ui>'''

        def __init__(self):
                super(MonkeysignScan, self).__init__()

                self.md = [] # modal dialogs to destroy

                # Set up main window
                self.set_title(_('Monkeysign (scan)'))
                self.set_position(gtk.WIN_POS_CENTER)
                self.connect("destroy", self.destroy)

                # Menu
                uimanager = gtk.UIManager()
                accelgroup = uimanager.get_accel_group()
                self.add_accel_group(accelgroup)
                actiongroup = gtk.ActionGroup('MonkeysignGen_Menu')
                actiongroup.add_actions([
                                ('File', None, _('_File')),
                                ('Open image...', gtk.STOCK_OPEN, _('Open image...'), None, None, self.import_image),
                                ('Save as...', gtk.STOCK_SAVE, _('_Save as...'), None, None, self.save_qrcode),
                                ('Print', gtk.STOCK_PRINT, _('_Print'), None, None, self.print_op),
                                ('Edit', None, '_Edit'),
                                ('Copy', gtk.STOCK_COPY, _('_Copy'), None, _('Copy image to clipboard'), self.clip_qrcode),
                                ('Quit', gtk.STOCK_QUIT, _('_Quit'), None, None, self.destroy),
                                ])
                uimanager.insert_action_group(actiongroup, 0)
                uimanager.add_ui_from_string(self.ui)

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
                        self.zbarframe = camframe
                        error_icon = gtk.Image()
                        error_icon.set_from_stock(gtk.STOCK_DIALOG_ERROR, gtk.ICON_SIZE_DIALOG)
                        vbox = gtk.VBox()
                        error_icon_bottom = gtk.Alignment(0, 1, 1, 0)
                        error_icon_bottom.add(error_icon)
                        error_label_top = gtk.Alignment(0, 0, 1, 0)
                        error_label_top.add(gtk.Label(_('No video device detected.')))
                        vbox.pack_start(error_icon_bottom)
                        vbox.pack_start(error_label_top)
                        vbox.set_size_request(320, 320)
                        camframe.add(vbox)
                        self.zbar = vbox

		# Ultimate keys list
                self.ultimate_keys = Keyring().get_keys(None, True, False).values() # Keep ultimately trusted keys in memory
                self.mykey = gtk.combo_box_new_text()

		cell = gtk.CellRendererText()
		cell.props.ellipsize = pango.ELLIPSIZE_END
                i = 0
                actions = []
		for key in self.ultimate_keys:
                        self.mykey.append_text(key.uidslist[0].uid)
                        i += 1
                if (i > 0):
                        self.mykey.set_active(0)

                # QR code display
                self.pixbuf = None # Hold QR code in pixbuf
                self.last_allocation = gtk.gdk.Rectangle() # Remember last allocation when resizing
                self.printsettings = None # Initialise print settings
                self.connect("expose-event", self.expose_event) # hook up to resize events

                self.qrcode = gtk.Image() # QR Code widget
                save = gtk.Button(stock=gtk.STOCK_SAVE) # Save button
                save.connect("clicked", self.save_qrcode);
                printbtn = gtk.Button(stock=gtk.STOCK_PRINT) # Print button
                printbtn.connect("clicked", self.print_op);
                self.clip = gtk.Clipboard() # Clipboard

		self.last_allocation = self.get_allocation()

                # Setup window layout
                mainvbox = gtk.VBox()
                mainhbox = gtk.HBox()
                lvbox = gtk.VBox()
                lvbox.pack_start(self.video_cb, False, False)
                lvbox.pack_start(self.zbarframe, False, False, 5)
                mainhbox.pack_start(lvbox, False, False, 10)
                mainvbox.pack_start(uimanager.get_widget('/MenuBar'), False, False)
                mainvbox.pack_start(self.mykey, False, False)
                mainvbox.pack_start(mainhbox, False, False, 10)
                self.add(mainvbox)

		# Setup window layout
		hbox = gtk.HBox(False, 2)
		vbox = gtk.VBox(False, 2)
		self.swin = gtk.ScrolledWindow()
		self.swin.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
		self.swin.add_with_viewport(self.qrcode)
		vbox.pack_start(self.swin, True, True, 0)
		hbox_btns = gtk.HBox(False, 2)
		hbox_btns.pack_start(save, False, False, 3)
		hbox_btns.pack_start(printbtn, False, False, 3)
		halign = gtk.Alignment(0.5, 0, 0, 0)
		halign.add(hbox_btns)
		vbox.pack_start(halign, False, False, 3)
		hbox.pack_start(vbox, True, True, 10)
		mainhbox.pack_start(hbox, True, True, 10)
                self.mykey.connect("changed", self.key_changed)

                # Start the show
                self.show_all()

	def expose_event(self, widget, event):
		"""When window is resized, regenerate the QR code"""
		if self.get_allocation() != self.last_allocation:
			self.last_allocation = self.get_allocation()
			self.key_changed()

        def key_changed(self, action=None, current=None, user_data=None):
		"""When another key is chosen, generate new QR code"""
                x = self.mykey.get_active();
                fpr = self.ultimate_keys[x].fpr
		self.pixbuf = self.image_to_pixbuf(self.make_qrcode(fpr))
		self.qrcode.set_from_pixbuf(self.pixbuf)

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

	def make_qrcode(self, fingerprint):
		"""Given a fingerprint, generate a QR code with appropriate prefix"""
		rect = self.swin.get_allocation()
		if rect.width < rect.height:
			size = rect.width - 15
		else:
			size = rect.height - 15
		version, width, image = _qrencode_scaled('OPENPGP4FPR:'+fingerprint,size,0,1,2,True)
		return image

        def import_image(self, widget):
               """Use a file chooser dialog to import an image containing a QR code"""
               self.dialog = gtk.FileChooserDialog("Open QR code image", None, gtk.FILE_CHOOSER_ACTION_OPEN, (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK))
               self.dialog.set_default_response(gtk.RESPONSE_OK)
               response = self.dialog.run()
               if response == gtk.RESPONSE_OK:
                               filename = self.dialog.get_filename()
                               gtk.gdk.threads_leave() # XXX: without this, the ask() method later freeze, go figure
                               #raise NotImplementedError(_('need to verify fingerprint on image!'))
                               self.scan_image(filename)
               self.dialog.destroy()
               return

        def scan_image(self, filename):
                """Scan an image for QR codes"""
                # create a reader
                scanner = zbar.ImageScanner()

                # configure the reader
                scanner.parse_config('enable')

                # obtain image data
                image = Image.open(filename)
                pil = image.convert('L')
                width, height = pil.size
                raw = pil.tostring()

                # wrap image data
                rawimage = zbar.Image(width, height, 'Y800', raw)

                # scan the image for barcodes
                scanner.scan(rawimage)

                # extract results
                for symbol in rawimage:
                        self.capture = gtk.Image()
                        self.capture.set_from_file(filename)
                        self.capture.show()
                        self.zbarframe.remove(self.zbar)
                        self.zbarframe.add(self.capture)
                        self.zbarframe.set_shadow_type(gtk.SHADOW_ETCHED_IN)

                        self.process_scan(symbol.data)

	def save_qrcode(self, widget=None):
		"""Use a file chooser dialog to enable user to save the current QR code as a PNG image file"""
		key = self.ultimate_keys[self.mykey.get_active()]
		image = self.make_qrcode(key.fpr)
		dialog = gtk.FileChooserDialog(_('Save QR code'), None, gtk.FILE_CHOOSER_ACTION_SAVE, (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_SAVE, gtk.RESPONSE_OK))
		dialog.set_default_response(gtk.RESPONSE_OK)
		dialog.set_current_name(key.keyid() + '.png')
		dialog.show()
		response = dialog.run()
		if response == gtk.RESPONSE_OK:
				name = dialog.get_filename()
				image.save(name, 'PNG')
		elif response == gtk.RESPONSE_CANCEL:
				pass
		dialog.destroy()
		return

	def clip_qrcode(self, widget=None):
		self.clip.set_image(self.pixbuf)

	def print_op(self, widget=None):
		keyid = self.ultimate_keys[self.mykey.get_active()].subkeys[0].keyid()
		print_op = gtk.PrintOperation()
		print_op.set_job_name('Monkeysign-'+keyid)
		print_op.set_n_pages(1)
		print_op.connect("draw_page", self.print_qrcode)
		res = print_op.run(gtk.PRINT_OPERATION_ACTION_PRINT_DIALOG, self)

	def print_qrcode(self, operation=None, context=None, page_nr=None):
		ctx = context.get_cairo_context()
		ctx.set_source_pixbuf(self.pixbuf, 0, 0)
		ctx.paint()
		ctx.restore()
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

        def update_progress_callback(self, *args):
                """callback invoked for pulsating progressbar
                """
                if self.keep_pulsing:
                        self.progressbar.pulse()
                        return True
                else:
                        return False

        def watch_out_callback(self, pid, condition):
                """callback invoked when gpg key download is finished
                """
                self.keep_pulsing=False
                self.dialog.destroy()
                self.msui.log(_('fetching finished'))
                if condition == 0:
                        # 2. copy the signing key secrets into the keyring
                        self.msui.copy_secrets()
                        # 3. for every user id (or all, if -a is specified)
                        # 3.1. sign the uid, using gpg-agent
                        self.msui.sign_key()

                        # 3.2. export and encrypt the signature
                        # 3.3. mail the key to the user
                        self.msui.export_key()

                        # 3.4. optionnally (-l), create a local signature and import in
                        #local keyring
                        # 4. trash the temporary keyring

                        self.resume_capture()
                        for md in self.md: md.destroy()
                return

        def decoded(self, zbar, data):
                """callback invoked when a barcode is decoded by the zbar widget.
                checks for an openpgp fingerprint
                """

                # Capture and display the video frame containing QR code
                self.zbarframe.set_shadow_type(gtk.SHADOW_NONE)
                alloc = self.zbarframe.allocation
                pixbuf = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, True, 8, alloc.width, alloc.height)
                pixbuf.get_from_drawable(self.zbarframe.window, self.zbarframe.window.get_colormap(),   alloc.x, alloc.y, 0, 0, alloc.width, alloc.height)
                self.capture = gtk.Image()
                self.capture.set_from_pixbuf(pixbuf)
                self.capture.show()
                self.zbarframe.remove(self.zbar)
                self.zbarframe.add(self.capture)
                self.zbarframe.set_shadow_type(gtk.SHADOW_ETCHED_IN)

                # Disable video capture
                self.zbar.set_video_enabled(False)

                self.process_scan(data)

        def process_scan(self, data):
                """process zbar-scanned data"""

                self.msui.log(_('zbar captured a frame, looking for 40 character hexadecimal fingerprint'))
                m = re.search("((?:[0-9A-F]{4}\s*){10})", data, re.IGNORECASE)

                if m != None:
                        # Found fingerprint, get it and strip spaces for GPG
                        # XXX: not sure why passing it into msui is necessary
                        self.msui.pattern = m.group(1).replace(' ', '')
                        # 1. fetch the key into a temporary keyring
                        # XXX: we override the find_key() because we want to be interactive
                        # but that's ugly as hell - find_key() should take a callback maybe?
                        # 1.a) from the local keyring
                        self.msui.log(_('looking for key %s in your keyring') % self.msui.pattern)
                        self.msui.keyring.context.set_option('export-options', 'export-minimal')
                        if self.msui.tmpkeyring.import_data(self.msui.keyring.export_data(self.msui.pattern)):
                                # XXXX: this actually hangs when signing the key, maybe because we're not in a callback?
                                # it's the prompting that hangs, see msui.ask...
                                self.watch_out_callback(0, 0) # XXX: hack, the callback should call a cleaner function
                                return # XXX: also ugly, reindent everything instead

                        # 1.b) if allowed (@todo), from the keyservers
                        if self.msui.options.keyserver is not None:
                                self.msui.tmpkeyring.context.set_option('keyserver', self.msui.options.keyserver)
                        command = self.msui.tmpkeyring.context.build_command(['recv-keys', self.msui.pattern])
                        self.msui.log('cmd: ' + str(command))
                        self.dialog = gtk.Dialog(title=_('Please wait'), parent=None, flags=gtk.DIALOG_MODAL, buttons=None)
                        self.dialog.add_button('gtk-cancel', gtk.RESPONSE_CANCEL)
                        message = gtk.Label(_('Retrieving public key from server...'))
                        message.show()
                        self.progressbar = gtk.ProgressBar()
                        self.progressbar.show()
                        self.dialog.vbox.pack_start(message, True, True, 5)
                        self.dialog.vbox.pack_start(self.progressbar, False, False, 5)
                        self.dialog.set_size_request(250, 100)
                        self.keep_pulsing = True
                        proc = subprocess.Popen(command, 0, None, subprocess.PIPE, subprocess.PIPE, subprocess.PIPE)
                        gobject.child_watch_add(proc.pid, self.watch_out_callback)
                        gobject.timeout_add(100, self.update_progress_callback)
                        if self.dialog.run() == gtk.RESPONSE_CANCEL:
                                proc.kill()
                else:
                        self.msui.warn(_('data found in barcode does not match a OpenPGP fingerprint pattern: %s') % data)
                        self.resume_capture()

        def resume_capture(self):
                self.zbarframe.remove(self.capture)
                try:
                        self.zbar.set_video_enabled(True)
                except AttributeError:
                        # the "zbar" is not a video frame capture, webcam probably disable, ignore
                        pass
                self.zbarframe.add(self.zbar)
                self.capture = None

        def destroy(self, widget, data=None):
                self.zbar.set_video_enabled(False)
                del self.msui
                gtk.main_quit()
