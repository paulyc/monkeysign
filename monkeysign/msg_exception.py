# bug-triage -- bug triage and forward tool.
# Copyright (C) 2007  Gustavo R. Montesino
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import pygtk
pygtk.require("2.0")
import gtk
import monkeysign.translation

def msg_exception(exception):
    """Shows information about a exception in a gtk dialog"""

    msg = ExceptionDialog(exception)
    msg.run()
    msg.destroy()

def errorhandler(f):
    """Error handler decorator"""
    def wrapper(*args, **kargs):
        try:
            return f(*args, **kargs)
        except Exception as instance:
            if type(instance) not in [KeyboardInterrupt, SystemExit]:
                msg_exception(instance)
    return wrapper

class ExceptionDialog(gtk.MessageDialog):
    def __init__(self, instance):
        gtk.MessageDialog.__init__(self, buttons=gtk.BUTTONS_CLOSE, type=gtk.MESSAGE_ERROR)
        self.set_resizable(True)
        self.set_markup(_("An error has occured:\n%r\nYou should save "
                "your work and restart the application. If the error "
                "occurs again please report it to the developer." % str(instance)))
        self.set_title(_("Error"))

class test:
    @errorhandler
    def __init__(self):
        raise Exception("test exception")

if __name__ == '__main__':
    test()
            
# vim: tabstop=4 expandtab shiftwidth=4     
