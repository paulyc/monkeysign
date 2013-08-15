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

import os
import sys
import msgfmt
from distutils.command.build import build
from distutils.core import Command

# stolen from deluge-1.3.3 (GPL3)
class build_trans(Command):
    description = 'Compile .po files into .mo files'

    user_options = [
            ('build-lib', None, "lib build folder")
    ]

    def initialize_options(self):
        self.build_lib = None

    def finalize_options(self):
        self.set_undefined_options('build', ('build_lib', 'build_lib'))

    def run(self):
        po_dir = os.path.join(os.path.dirname(__file__), 'po/')

        print('Compiling po files from %s...' % po_dir),
        uptoDate = False
        for path, names, filenames in os.walk(po_dir):
            for f in filenames:
                uptoDate = False
                if f.endswith('.po'):
                    lang = f[:len(f) - 3]
                    src = os.path.join(path, f)
                    dest_path = os.path.join(self.build_lib, 'gameclock', 'po', lang, \
                        'LC_MESSAGES')
                    dest = os.path.join(dest_path, 'gameclock.mo')
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
            sys.stdout.write(' po files already upto date.  ')
        sys.stdout.write('\b\b \nFinished compiling translation files. \n')

build.sub_commands.append(('build_trans', None))
