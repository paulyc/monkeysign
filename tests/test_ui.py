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

"""
Test suite for the basic user interface class.
"""

import unittest
import os
import sys

sys.path.append(os.path.dirname(__file__) + '/..')

from monkeysign.ui import MonkeysignUi
from monkeysign.gpg import TempKeyring

from test_lib import TestTimeLimit

class CliBaseTest(unittest.TestCase):
    def setUp(self):
        self.argv = sys.argv
        sys.argv = [ 'monkeysign', '--dry-run', '--no-mail' ]

    def tearDown(self):
        sys.argv = self.argv

class CliTestCase(CliBaseTest):
    def test_call_usage(self):
        with self.assertRaises(SystemExit):
            execfile(os.path.dirname(__file__) + '/../scripts/monkeysign')

class CliTestDialog(CliBaseTest):
    def setUp(self):
        CliBaseTest.setUp(self)
        self.gpg = TempKeyring()
        os.environ['GNUPGHOME'] = self.gpg.homedir
        self.assertTrue(self.gpg.import_data(open(os.path.dirname(__file__) + '/7B75921E.asc').read()))
        self.assertTrue(self.gpg.import_data(open(os.path.dirname(__file__) + '/96F47C6A.asc').read()))
        self.assertTrue(self.gpg.import_data(open(os.path.dirname(__file__) + '/96F47C6A-secret.asc').read()))
        
        sys.argv += [ '-u', '96F47C6A', '7B75921E' ]

    def write_to_callback(self, stdin, callback):
        r, w = os.pipe()
        pid = os.fork()
        if pid:
            # parent
            os.close(w)
            os.dup2(r, 0) # make stdin read from the child
            oldstdout = sys.stdout
            sys.stdout = open('/dev/null', 'w') # silence output
            callback(self)
            sys.stdout = oldstdout
        else:
            # child
            os.close(r)
            w = os.fdopen(w, 'w')
            w.write(stdin) # say whatever is needed to msign-cli
            w.flush()
            os._exit(0)

    def test_sign_fake_keyring(self):
        """test if we can sign a key on a fake keyring"""
        def callback(self):
            execfile(os.path.dirname(__file__) + '/../scripts/monkeysign')
        self.write_to_callback("y\n", callback) # just say yes

    def test_two_empty_responses(self):
        """test what happens when we answer nothing twice"""
        def callback(self):
            with self.assertRaises(EOFError):
                execfile(os.path.dirname(__file__) + '/../scripts/monkeysign')
        self.write_to_callback("\n\n", callback) # just say yes

class BaseTestCase(unittest.TestCase):
    pattern = None
    args = []

    def setUp(self):
        self.args = [ '--no-mail' ] + self.args + [ x for x in sys.argv[1:] if x.startswith('-') ]
        if self.pattern is not None:
            self.args += [ self.pattern ]
        self.ui = MonkeysignUi(self.args)
        self.ui.keyring = TempKeyring()
        self.ui.prepare() # needed because we changed the base keyring

class BasicTests(BaseTestCase):
    pattern = '7B75921E'

    def setUp(self):
        BaseTestCase.setUp(self)
        self.homedir = self.ui.tmpkeyring.homedir

    def test_cleanup(self):
        del self.ui
        self.assertFalse(os.path.exists(self.homedir))

class SigningTests(BaseTestCase):
    pattern = '7B75921E'

    def setUp(self):
        """setup a basic keyring capable of signing a local key"""
        BaseTestCase.setUp(self)
        self.assertTrue(self.ui.keyring.import_data(open(os.path.dirname(__file__) + '/7B75921E.asc').read()))
        self.assertTrue(self.ui.tmpkeyring.import_data(open(os.path.dirname(__file__) + '/96F47C6A.asc').read()))
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
        self.assertTrue(self.ui.keyring.get_keys(None, True, False))
        self.assertGreaterEqual(len(self.ui.keyring.get_keys(None, True, False)), 1)
        self.assertGreaterEqual(len(self.ui.keyring.get_keys(None, True, True)), 1)

    def test_sign_key(self):
        """test if we can sign the keys non-interactively"""
        self.test_copy_secrets()
        self.ui.sign_key()
        self.assertGreaterEqual(len(self.ui.signed_keys), 1)

    def test_create_mail(self):
        """test if the exported keys are signed"""
        self.test_sign_key()

        for fpr, key in self.ui.signed_keys.items():
            msg = self.ui.create_mail(fpr, 'unittests@localhost', 'devnull@localhost')
            self.assertIsNotNone(msg)
            self.assertRegexpMatches(msg.as_string(), "BEGIN PGP MESSAGE")

    @unittest.expectedFailure
    def test_create_mail_multiple(self):
        """test if exported keys contain the right uid

not yet implemented, see the TODO in export_key() for more details"""
        self.test_sign_key()

        for fpr, key in self.ui.signed_keys.items():
            oldmsg = None
            for uid in key.uids.values():
                msg = self.ui.create_mail(uid, 'unittests@localhost', 'devnull@localhost')
                if oldmsg is not None:
                    self.assertNotEqual(oldmsg, msg)

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

class NonExistantKeyTests(BaseTestCase, TestTimeLimit):
    """test behavior with a key that can't be found"""

    args = []
    # odds that a key with all zeros as fpr are low, unless something happens between PGP and bitcoins...
    pattern = '0000000000000000000000000000000000000000'

    def test_find_key(self):
        """find_key() should exit if the key can't be found on keyservers or local keyring"""
        with self.assertRaises(SystemExit):
            self.ui.find_key()

if __name__ == '__main__':
    unittest.main()
