#!/usr/bin/env python

import sys

try:
    from gi.repository import Gtk
except:
    print "You need to install pyGTK or GTKv2 ",
    sys.exit(1)

class Handler:
    """
    This handler gets called by Gtk.Builder() based on the signals
    defined in the XML UI.
    """
    def quit(self, *args):
        Gtk.main_quit(*args)

    def button(self, button):
        print "Hello World!"
        print "I am a button!" + repr(button)

class monkeysharegui:
    """
    This class builds the UI from the glade files and shows all
    windows, but doesn't start the GTK threads.
    """
    def __init__(self):
        """
        """
        builder = Gtk.Builder()
        builder.add_from_file(sys.argv[1])
        builder.connect_signals(Handler())
        window = builder.get_object(sys.argv[2])
        window.show_all()
        return

try:
    monkeysharegui()
except IndexError:
    print "pass the name of the glade file to load and the name of the main window"
    sys.exit(1)
except AttributeError:
    print "wrong window name"
    sys.exit(1)
Gtk.main()
