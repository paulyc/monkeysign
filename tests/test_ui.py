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
import re

sys.path.append(os.path.dirname(__file__) + '/..')

from monkeysign.ui import MonkeysignUi, EmailFactory
from monkeysign.gpg import TempKeyring

from test_lib import TestTimeLimit

class CliBaseTest(unittest.TestCase):
    def setUp(self):
        self.argv = sys.argv
        sys.argv = [ 'monkeysign', '--no-mail' ]

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

    def test_create_mail_multiple(self):
        """test if exported keys contain the right uid"""
        self.test_sign_key()

        for fpr, key in self.ui.signed_keys.items():
            oldmsg = None
            for uid in key.uids.values():
                msg = EmailFactory(self.ui.tmpkeyring.export_data(fpr), fpr, uid.uid, 'unittests@localhost', 'devnull@localhost')
                if oldmsg is not None:
                    self.assertNotEqual(oldmsg.as_string(), msg.as_string())
                    self.assertNotEqual(oldmsg.create_mail_from_block(oldmsg.tmpkeyring.export_data(fpr)).as_string(),
                                        msg.create_mail_from_block(oldmsg.tmpkeyring.export_data(fpr)).as_string())
                    self.assertNotEqual(oldmsg.tmpkeyring.export_data(fpr),
                                        msg.tmpkeyring.export_data(fpr))
                oldmsg = msg
            self.assertIsNot(oldmsg, None)

class EmailFactoryTest(BaseTestCase):
    pattern = '7B75921E'

    def setUp(self):
        """setup a basic keyring capable of signing a local key"""
        BaseTestCase.setUp(self)
        self.assertTrue(self.ui.tmpkeyring.import_data(open(os.path.dirname(__file__) + '/7B75921E.asc').read()))
        self.assertTrue(self.ui.tmpkeyring.import_data(open(os.path.dirname(__file__) + '/96F47C6A.asc').read()))
        self.assertTrue(self.ui.tmpkeyring.import_data(open(os.path.dirname(__file__) + '/96F47C6A-secret.asc').read()))

        self.email = EmailFactory(self.ui.tmpkeyring.export_data(self.pattern), self.pattern, 'Antoine Beaupré <anarcat@orangeseeds.org>', 'nobody@example.com', 'nobody@example.com')

    def test_cleanup_uids(self):
        """test if we can properly remove irrelevant UIDs"""
        for fpr, key in self.email.tmpkeyring.get_keys('7B75921E').iteritems():
            for u, uid in key.uids.iteritems():
                self.assertEqual(self.email.recipient, uid.uid)

    def test_mail_key(self):
        """test if we can generate a mail with a key inside"""
        data = self.email.tmpkeyring.export_data(self.pattern)
        self.assertNotEqual(data, '')
        message = self.email.create_mail_from_block(data)
        match = re.compile("""Content-Type: multipart/mixed; boundary="===============%s=="
MIME-Version: 1.0

--===============%s==
Content-Type: text/plain; charset="utf-8"
MIME-Version: 1.0
Content-Transfer-Encoding: base64

ClBsZWFzZSBmaW5kIGF0dGFjaGVkIHlvdXIgc2lnbmVkIFBHUCBrZXkuIFlvdSBjYW4gaW1wb3J0
IHRoZSBzaWduZWQKa2V5IGJ5IHJ1bm5pbmcgZWFjaCB0aHJvdWdoIGBncGcgLS1pbXBvcnRgLgoK
Tm90ZSB0aGF0IHlvdXIga2V5IHdhcyBub3QgdXBsb2FkZWQgdG8gYW55IGtleXNlcnZlcnMuIElm
IHlvdSB3YW50CnRoaXMgbmV3IHNpZ25hdHVyZSB0byBiZSBhdmFpbGFibGUgdG8gb3RoZXJzLCBw
bGVhc2UgdXBsb2FkIGl0CnlvdXJzZWxmLiAgV2l0aCBHbnVQRyB0aGlzIGNhbiBiZSBkb25lIHVz
aW5nOgoKICAgIGdwZyAtLWtleXNlcnZlciBwb29sLnNrcy1rZXlzZXJ2ZXJzLm5ldCAtLXNlbmQt
a2V5IDxrZXlpZD4KClJlZ2FyZHMsCg==

--===============%s==
Content-Type: application/pgp-keys; name="yourkey.asc"
MIME-Version: 1.0
Content-Disposition: attachment; filename="yourkey.asc"
Content-Transfer-Encoding: 7bit
Content-Description: PGP Key <keyid>, uid <uid> \(<idx\), signed by <keyid>

-----BEGIN PGP PUBLIC KEY BLOCK-----
.*
-----END PGP PUBLIC KEY BLOCK-----

--===============%s==--""" % tuple([ '[0-9]*' ] * 4), re.DOTALL)
        self.assertRegexpMatches(message.as_string(), match)
        return message

    def test_wrap_crypted_mail(self):
        match = re.compile("""Content-Type: multipart/encrypted; protocol="application/pgp-encrypted";
 boundary="===============%s=="
MIME-Version: 1.0
Subject: Your signed OpenPGP key
From: nobody@example.com
To: nobody@example.com

This is a multi-part message in PGP/MIME format...
--===============%s==
Content-Type: application/pgp-encrypted; filename="signedkey.msg"
MIME-Version: 1.0
Content-Disposition: attachment; filename="signedkey.msg"

Version: 1
--===============%s==
Content-Type: application/octet-stream; filename="msg.asc"
MIME-Version: 1.0
Content-Disposition: inline; filename="msg.asc"
Content-Transfer-Encoding: 7bit

-----BEGIN PGP MESSAGE-----
.*
-----END PGP MESSAGE-----

--===============%s==--""" % tuple(['[0-9]*'] * 4), re.DOTALL)
        self.assertRegexpMatches(self.email.as_string(), match)

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
        try:
            with self.assertRaises(SystemExit):
                self.ui.find_key()
        except AlarmException:
            raise unittest.case._ExpectedFailure(sys.exc_info())

if __name__ == '__main__':
    unittest.main()
