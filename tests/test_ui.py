#!/usr/bin/pytho
# -*- coding: utf-8 -*-

"""
Test suite for the basic user interface class.
"""

import unittest
import os
import sys

sys.path.append(os.path.dirname(__file__) + '/..')

from monkeysign.ui import MonkeysignUi
from monkeysign.gpg import TempKeyring

class BaseTestCase(unittest.TestCase):
    def setUp(self):
        (self.options, self.args) = MonkeysignUi.parse_args()
        self.options.dryrun = True
        self.options.nomail = True

class BasicTests(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.ui = MonkeysignUi(self.options, '7B75921E')
        self.tmphomedir = self.ui.tmpkeyring.tmphomedir
        self.ui.keyring = TempKeyring()

    def test_cleanup(self):
        del self.ui
        self.assertFalse(os.path.exists(self.tmphomedir))

    def test_find_key(self):
        """this should find the key on the keyservers"""
        self.ui.find_key()

class FakeKeyringTests(BaseTestCase):
    def setUp(self):
        """we setup a fake keyring with the public key to sign and add our private keys"""
        BaseTestCase.setUp(self)
        self.ui = MonkeysignUi(self.options, '96F47C6A')
        self.ui.keyring = TempKeyring()
        self.ui.keyring.import_data(open(os.path.dirname(__file__) + '/96F47C6A.asc').read())

    def test_find_key(self):
        """test if we can find a key on the local keyring"""
        self.ui.find_key()

class NonExistantKeyTests(BaseTestCase):
    """test behavior with a key that can't be found"""
    def setUp(self):
        """odds that a key with all zeros as fpr are low, unless something happens between PGP and bitcoins..."""
        BaseTestCase.setUp(self)
        self.ui = MonkeysignUi(self.options, '0000000000000000000000000000000000000000')

    def test_find_key(self):
        """find_key() should exit if the key can't be found on keyservers or local keyring"""
        with self.assertRaises(SystemExit):
            self.ui.find_key()
