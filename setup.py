#!/usr/bin/python
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

from distutils.core import setup
from glob import glob

from monkeysign import __version__ as version
import monkeysign.manpage
import monkeysign.translation

setup(name = 'monkeysign',
    description='OpenPGP key exchange for humans',
    long_description="""
monkeysign is a tool to overhaul the OpenPGP keysigning experience and
bring it closer to something that most primates can understand.

The project makes use of cheap digital cameras and the type of bar
code known as a QRcode to provide a human-friendly yet still-secure
keysigning experience.

No more reciting tedious strings of hexadecimal characters.  And, you
can build a little rogue's gallery of the people that you have met and
exchanged keys with!
""",
    version=version,
    author='Antoine Beaupré',
    author_email='anarcat@debian.org',
    url='http://web.monkeysphere.info/',
    packages=['monkeysign'],
    scripts=['scripts/monkeysign', 'scripts/monkeyscan'],
    cmdclass={'build_manpage': monkeysign.manpage.build_manpage,
              'build_trans': monkeysign.translation.build_trans},
    data_files=[('share/man/man1', glob('man/*.1'))],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: Information Technology',
        'Intended Audience :: Legal Industry',
        'Intended Audience :: Telecommunications Industry',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 2.4',
        'Programming Language :: Python :: 2.5',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Operating System :: OS Independent',
        'Environment :: X11 Applications :: GTK',
        'Environment :: Console',
        'Natural Language :: English',
        'Topic :: Communications :: Email',
        'Topic :: Multimedia :: Video :: Capture',
        'Topic :: Security :: Cryptography',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
)
