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

class CliTestCase(unittest.TestCase):
    def setUp(self):
        self.argv = sys.argv
        sys.argv = [ 'msign-cli', '--dry-run', '--no-mail' ]

    def test_call_usage(self):
        with self.assertRaises(SystemExit):
            execfile(os.path.dirname(__file__) + '/../msign')

    def tearDown(self):
        sys.argv = self.argv

class BaseTestCase(unittest.TestCase):
    pattern = None
    args = []

    def setUp(self):
        self.args = [ '--no-mail' ] + self.args + [ x for x in sys.argv[1:] if x.startswith('-') ]
        if self.pattern is not None:
            self.args += [ self.pattern ]
        self.ui = MonkeysignUi(self.args)
        self.ui.keyring = TempKeyring()

class BasicTests(BaseTestCase):
    pattern = '7B75921E'

    def setUp(self):
        BaseTestCase.setUp(self)
        self.tmphomedir = self.ui.tmpkeyring.tmphomedir

    def test_cleanup(self):
        del self.ui
        self.assertFalse(os.path.exists(self.tmphomedir))

class SigningTests(BaseTestCase):
    pattern = '7B75921E'

    def setUp(self):
        """setup a basic keyring capable of signing a local key"""
        BaseTestCase.setUp(self)
        self.assertTrue(self.ui.keyring.import_data(open(os.path.dirname(__file__) + '/7B75921E.asc').read()))
        self.assertTrue(self.ui.keyring.import_data(open(os.path.dirname(__file__) + '/96F47C6A.asc').read()))
        self.assertTrue(self.ui.keyring.import_data(open(os.path.dirname(__file__) + '/96F47C6A-secret.asc').read()))

    def test_find_key(self):
        """test if we can extract the key locally

this duplicates tests from the gpg code, but is necessary to test later functions"""
        self.ui.find_key()

    def test_copy_secrets(self):
        """test if we can copy secrets between the two keyrings

this duplicates tests from the gpg code, but is necessary to test later functions"""
        self.test_find_key()
        self.ui.copy_secrets()

    def test_sign_key(self):
        """test if we can sign the keys non-interactively"""
        self.test_copy_secrets()
        self.ui.sign_key()
        self.assertGreaterEqual(len(self.ui.signed_keys), 1)

    def test_create_mail(self):
        """test if the exported keys are signed"""
        self.test_sign_key()

        # XXX: this duplicates code from export_key(), not good.
        self.ui.tmpkeyring.context.set_option('armor')
        self.ui.tmpkeyring.context.set_option('always-trust')
        from_user = self.ui.signing_key.uidslist[0].uid

        for fpr, key in self.ui.signed_keys.items():
            data = self.ui.tmpkeyring.export_data(fpr)
            msg = self.ui.create_mail(self.ui.pattern, data, from_user, 'devnull@localhost')
            self.assertIsNotNone(msg)

class KeyserverTests(BaseTestCase):
    args = [ '--keyserver', 'pool.sks-keyservers.net' ]
    pattern = '7B75921E'

    def test_find_key(self):
        """this should find the key on the keyservers"""
        self.ui.find_key()

class FakeKeyringTests(BaseTestCase):
    args = []
    pattern = '96F47C6A'

    def setUp(self):
        """we setup a fake keyring with the public key to sign and add our private keys"""
        BaseTestCase.setUp(self)
        self.ui.keyring.import_data(open(os.path.dirname(__file__) + '/96F47C6A.asc').read())

    def test_find_key(self):
        """test if we can find a key on the local keyring"""
        self.ui.find_key()

class NonExistantKeyTests(BaseTestCase):
    """test behavior with a key that can't be found"""

    args = []
    # odds that a key with all zeros as fpr are low, unless something happens between PGP and bitcoins...
    pattern = '0000000000000000000000000000000000000000'

    def test_find_key(self):
        """find_key() should exit if the key can't be found on keyservers or local keyring"""
        with self.assertRaises(SystemExit):
            self.ui.find_key()
