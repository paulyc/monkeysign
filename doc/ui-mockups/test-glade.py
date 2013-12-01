#!/usr/bin/env python

import sys

try:
    from gi.repository import Gtk
except:
    print "You need to install pyGTK or GTKv2 ",
    sys.exit(1)


class monkeysharegui:
    def __init__(self):
        """
        """
        builder = Gtk.Builder()
        builder.add_from_file("share-ui.glade")
        window = builder.get_object("monkeyshare")
        window.show_all()
        return

    def button1_clicked(self,widget):
        print "button clicked"

monkeysharegui()
Gtk.main()
