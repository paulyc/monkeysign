# -*- coding: utf-8 -*-

from distutils.core import setup

from gpg import __version__ as version

setup(name = 'monkeysign',
    description='OpenPGP key exchange for humans',
    long_description='This tool makes it easier to sign and exchange OpenPGP keys.',
    version=version,
    author='Antoine Beaupré',
    author_email='anarcat@debian.org',
    url='http://web.monkeysphere.info/',
    py_modules=['gpg'],
    scripts=['monkeysign-cli', 'monkeysign-scan', 'monkeysign-gen'],
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
    ]
)
