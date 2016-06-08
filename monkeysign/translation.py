# -*- coding: utf-8 -*-
#
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

from __future__ import print_function
import os
import sys
import msgfmt
from distutils.command.build import build
from distutils.core import Command
import locale
import gettext
import pkg_resources

# Initialize gettext, taken from deluge 1.3.3 (GPL3)
try:
    locale.setlocale(locale.LC_ALL, '')
    if hasattr(locale, "bindtextdomain"):
        locale.bindtextdomain('monkeysign', pkg_resources.resource_filename('monkeysign', "po"))
    if hasattr(locale, "textdomain"):
        locale.textdomain('monkeysign')
    gettext.install('monkeysign', pkg_resources.resource_filename('monkeysign', "po"), unicode=True, names='ngettext')
except Exception as e:
    print ("Unable to initialize translations: %s" % e)
    import __builtin__
    __builtin__.__dict__["_"] = lambda x: x

# stolen from deluge-1.3.3 (GPL3)
class build_trans(Command):
    description = 'Compile .po files into .mo files'

    user_options = [
            ('build-lib=', None, "lib build folder"),
            ('po-dir=', 'p', 'directory where .po files are stored, relative to the current directory'),
    ]

    def initialize_options(self):
        self.build_lib = None
        self.po_dir = 'po/'

    def finalize_options(self):
        self.set_undefined_options('build', ('build_lib', 'build_lib'))

    def run(self):
        po_dir = self.po_dir

        appname = self.distribution.get_name()
        self.announce('compiling po files from %s' % po_dir, 2)
        uptoDate = False
        for path, names, filenames in os.walk(po_dir):
            for f in filenames:
                uptoDate = False
                if f.endswith('.po'):
                    lang = f[:len(f) - 3]
                    src = os.path.join(path, f)
                    dest_path = os.path.join(self.build_lib, appname, 'po', lang, \
                        'LC_MESSAGES')
                    dest = os.path.join(dest_path, appname + '.mo')
                    if not os.path.exists(dest_path):
                        os.makedirs(dest_path)
                    if not os.path.exists(dest):
                        sys.stdout.write('%s, ' % lang)
                        sys.stdout.flush()
                        msgfmt.make(src, dest)
                    else:
                        src_mtime = os.stat(src)[8]
                        dest_mtime = os.stat(dest)[8]
                        if src_mtime > dest_mtime:
                            sys.stdout.write('%s, ' % lang)
                            sys.stdout.flush()
                            msgfmt.make(src, dest)
                        else:
                            uptoDate = True
                            
        if uptoDate:
            self.announce('po files already upto date.', 2)
        else:
            self.announce('done', 2)


build.sub_commands.append(('build_trans', None))
