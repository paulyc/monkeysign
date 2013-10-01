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

def msg_exception(exception):
    """Shows information about a exception in a gtk dialog"""

    msg = gtk.MessageDialog(type=gtk.MESSAGE_ERROR, buttons=gtk.BUTTONS_CLOSE,
        message_format=exception.__class__.__name__)
    msg.format_secondary_text(exception.__str__())
    msg.set_title("Error")
    msg.run()
    msg.destroy()

def errorhandler(f):
    """Error handler decorator"""
    def wrapper(*args, **kargs):
        try:
            return f(*args, **kargs)
        except Exception, instance:
            msg_exception(instance)
    return wrapper
            
            
# vim: tabstop=4 expandtab shiftwidth=4     
