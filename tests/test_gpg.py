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

"""General test suite for the GPG API.

Tests that require network access should go in test_network.py.
"""

import sys, os, shutil
from StringIO import StringIO
import unittest
import tempfile
import re

sys.path.insert(0, os.path.dirname(__file__) + '/..')

from monkeysign.gpg import *

class TestContext(unittest.TestCase):
    """Tests for the Context class.

    Those should be limited to talking to the GPG binary, not
    operating on actual keyrings or GPG data."""

    # those need to match the options in the Gpg class
    options = Context.options

    # ... and this is the rendered version of the above
    rendered_options = ['gpg', '--command-fd', '0', '--with-fingerprint', '--list-options', 'show-sig-subpackets,show-uid-validity,show-unusable-uids,show-unusable-subkeys,show-keyring,show-sig-expire', '--batch', '--fixed-list-mode', '--no-tty', '--with-colons', '--use-agent', '--status-fd', '2', '--quiet' ]

    def setUp(self):
        self.gpg = Context()

    def test_plain(self):
        """make sure other instances do not poison us"""
        d = Context()
        d.set_option('homedir', '/var/nonexistent')
        self.assertNotIn('homedir', self.gpg.options)

    def test_set_option(self):
        """make sure setting options works"""
        self.gpg.set_option('armor')
        self.assertIn('armor', self.gpg.options)
        self.gpg.set_option('keyserver', 'foo.example.com')
        self.assertDictContainsSubset({'keyserver': 'foo.example.com'}, self.gpg.options)

    def test_command(self):
        """test various command creation

        if this fails, it's probably because you added default options
        to the tested class without adding them in the test class
        """
        c = self.rendered_options + ['--version']
        c2 = self.gpg.build_command(['version'])
        self.assertItemsEqual(c, c2)
        c = self.rendered_options + ['--export', 'foo']
        c2 = self.gpg.build_command(['export', 'foo'])
        self.assertItemsEqual(c, c2)

    def test_version(self):
        """make sure version() returns something"""
        self.assertTrue(self.gpg.version())

    def test_seek_debug(self):
        """test if seek actually respects debug"""
        self.gpg.debug = True # should yield an attribute error, that's fine
        with self.assertRaises(AttributeError):
            self.gpg.seek(StringIO('test'), 'test')
        # now within a keyring?
        k = TempKeyring()
        k.context.debug = True
        with self.assertRaises(AttributeError):
            k.import_data(open(os.path.dirname(__file__) + '/96F47C6A.asc').read())

class TestTempKeyring(unittest.TestCase):
    """Test the TempKeyring class."""

    def setUp(self):
        self.gpg = TempKeyring()
        self.assertIn('homedir', self.gpg.context.options)

    def tearDown(self):
        del self.gpg

class TestKeyringBase(unittest.TestCase):
    """Base class for Keyring class tests.

    This shouldn't implement any tests that we don't want to see
    implemented every time.
    """

    def setUp(self):
        """setup the test environment

        we test using a temporary keyring because it's too dangerous
        otherwise.

        we are not using the TempKeyring class however, because we may
        want to keep that data for examination later. see the
        tearDown() function for that.
        """
        self.tmp = tempfile.mkdtemp(prefix="pygpg-")
        self.gpg = Keyring(self.tmp)
        self.assertEqual(self.gpg.context.options['homedir'], self.tmp)

    def tearDown(self):
        """trash the temporary directory we created"""
        shutil.rmtree(self.tmp)

class TestKeyringBasics(TestKeyringBase):
    """Test the Keyring class base functionality."""

    def test_home(self):
        """test if the homedir is properly set and populated"""
        self.gpg.export_data('') # dummy call to make gpg populate his directory
        self.assertTrue(open(self.tmp + '/pubring.gpg'))

    def test_import(self):
        """make sure import_data returns true on known good data

        it should throw an exception if there's something wrong with the backend too
        """
        self.assertTrue(self.gpg.import_data(open(os.path.dirname(__file__) + '/96F47C6A.asc').read()))

    def test_import_fail(self):
        """test that import_data() throws an error on wrong data"""
        self.assertFalse(self.gpg.import_data(''))

    def test_export(self):
        """test that we can export data similar to what we import

        @todo this will probably fail if tests are ran on a different GPG version
        """
        self.assertTrue(self.gpg.import_data(open(os.path.dirname(__file__) + '/96F47C6A.asc').read()))
        k1 = re.sub(r'Version:.*$', r'', open(os.path.dirname(__file__) + '/96F47C6A.asc').read(), flags=re.MULTILINE)
        self.gpg.context.set_option('armor')
        self.gpg.context.set_option('export-options', 'export-minimal')
        self.gpg.context.set_option('no-emit-version')
        k2 = re.sub(r'Version:.*$', r'', self.gpg.export_data('96F47C6A'), flags=re.MULTILINE)
        self.assertEqual(k1,k2)

    def test_get_missing_secret_keys(self):
        """make sure we fail to get secret keys when they are missing"""
        self.assertTrue(self.gpg.import_data(open(os.path.dirname(__file__) + '/7B75921E.asc').read()))
        # this shouldn't show anything, as this is just a public key blob
        self.assertFalse(self.gpg.get_keys('8DC901CE64146C048AD50FBB792152527B75921E', True, False))

    def test_export_secret(self):
        """make sure we can import and export secret data"""
        self.assertTrue(self.gpg.import_data(open(os.path.dirname(__file__) + '/96F47C6A-secret.asc').read()))
        self.secret = self.gpg.export_data('96F47C6A', True)
        self.assertTrue(self.secret)

    def test_list_imported_secrets(self):
        """make sure we can print imported secrets"""
        self.assertTrue(self.gpg.import_data(open(os.path.dirname(__file__) + '/96F47C6A-secret.asc').read()))
        self.assertTrue(self.gpg.get_keys(None, True, False))

    def test_empty_keyring(self):
        """a test should work on an empty keyring

        this is also a test of exporting an empty keyring"""
        self.assertEqual(self.gpg.export_data(), '')

    def test_sign_key_missing_key(self):
        """try to sign a missing key

        this should fail because we don't have the public key material
        for the requested key

        however, gpg returns the wrong exit code here, so we end up at
        looking if there is really no output
        """
        self.assertTrue(self.gpg.import_data(open(os.path.dirname(__file__) + '/96F47C6A-secret.asc').read()))
        with self.assertRaises(GpgRuntimeError):
            self.gpg.sign_key('7B75921E')

    def test_failed_revoke(self):
        self.gpg.import_data(open(os.path.dirname(__file__) + '/96F47C6A.asc').read())
        self.gpg.import_data(open(os.path.dirname(__file__) + '/96F47C6A-revoke.asc').read())
        self.gpg.import_data(open(os.path.dirname(__file__) + '/7B75921E.asc').read())
        with self.assertRaises(GpgRuntimeError):
            self.gpg.sign_key('7B75921E', True)

class TestKeyringWithKeys(TestKeyringBase):
    def setUp(self):
        TestKeyringBase.setUp(self)
        self.assertTrue(self.gpg.import_data(open(os.path.dirname(__file__) + '/7B75921E.asc').read()))
        self.assertTrue(self.gpg.import_data(open(os.path.dirname(__file__) + '/96F47C6A.asc').read()))
        self.assertTrue(self.gpg.import_data(open(os.path.dirname(__file__) + '/96F47C6A-secret.asc').read()))

    def test_get_keys(self):
        """test that we can list the keys after importing them

        @todo we should check the data structure
        """
        # just a cute display for now
        for fpr, key in self.gpg.get_keys('96F47C6A').iteritems():
            print key

    def test_sign_key_wrong_user(self):
        """make sure sign_key with a erroneous local-user fails

        that is, even if all other conditions are ok"""
        self.gpg.context.set_option('local-user', '0000000F')
        with self.assertRaises(GpgRuntimeError):
            self.gpg.sign_key('7B75921E', True)

    def test_sign_key_all_uids(self):
        """test signature of all uids of a key"""
        self.assertTrue(self.gpg.sign_key('7B75921E', True))
        self.gpg.context.call_command(['list-sigs', '7B75921E'])
        self.assertRegexpMatches(self.gpg.context.stdout, 'sig:::1:86E4E70A96F47C6A:[^:]*::::Second Test Key <unittests@monkeysphere.info>:10x:')

    def test_sign_key_single_uid(self):
        """test signing a key with a single uid"""
        self.assertTrue(self.gpg.import_data(open(os.path.dirname(__file__) + '/323F39BD.asc').read()))
        self.assertTrue(self.gpg.sign_key('323F39BD', True))
        self.gpg.context.call_command(['list-sigs', '323F39BD'])
        self.assertRegexpMatches(self.gpg.context.stdout, 'sig:::1:A31E75E4323F39BD:[^:]*::::Monkeysphere second test key <bar@example.com>:[0-9]*x:')

    def test_sign_key_one_uid(self):
        """test signature of a single uid"""
        self.assertTrue(self.gpg.sign_key('Antoine Beaupré <anarcat@debian.org>'))
        self.gpg.context.call_command(['list-sigs', '7B75921E'])
        self.assertRegexpMatches(self.gpg.context.stdout, 'sig:::1:86E4E70A96F47C6A:[^:]*::::Second Test Key <unittests@monkeysphere.info>:10x:')

    def test_sign_key_as_user(self):
        """normal signature with a signing user specified"""
        self.gpg.context.set_option('local-user', '96F47C6A')
        self.assertTrue(self.gpg.sign_key('7B75921E', True))

    def test_sign_already_signed(self):
        """test if signing a already signed key fails with a meaningful message"""
        self.assertTrue(self.gpg.sign_key('Antoine Beaupré <anarcat@debian.org>'))
        with self.assertRaises(GpgRuntimeError):
            self.gpg.sign_key('Antoine Beaupré <anarcat@debian.org>')

    def test_encrypt_decrypt_data_armored_untrusted(self):
        """test if we can encrypt data to our private key (and decrypt it)"""
        plaintext = 'i come in peace'

        # we trust all keys blindly to avoid having to set trust on that key
        self.gpg.context.set_option('trust-model', 'always')
        self.gpg.context.set_option('armor')
        cyphertext = self.gpg.encrypt_data(plaintext, '96F47C6A')
        self.assertTrue(cyphertext)

        p = self.gpg.decrypt_data(cyphertext)
        self.assertTrue(p)
        self.assertEqual(p, plaintext)

    def test_gen_key(self):
        """test key generation

        not implemented"""
        #self.fpr = self.gpg.gen_key()
        #self.assertTrue(self.fpr)
        pass

    def test_multi_secrets(self):
        """test if we get confused with multiple secret keys"""

        self.assertTrue(self.gpg.import_data(open(os.path.dirname(__file__) + '/323F39BD.asc').read()))
        self.assertTrue(self.gpg.import_data(open(os.path.dirname(__file__) + '/323F39BD-secret.asc').read()))

        keys = self.gpg.get_keys(None, True, False)
        self.assertEqual(len(keys.keys()), 2)
        #for fpr, key in keys.iteritems():
        #    print >>sys.stderr, "key:", key

    def test_del_uid(self):
        """test uid deletion, gpg.del_uid()"""
        userid = 'Antoine Beaupré <anarcat@orangeseeds.org>'
        self.assertTrue(self.gpg.import_data(open(os.path.dirname(__file__) + '/7B75921E.asc').read()))
        found = False
        keys = self.gpg.get_keys('7B75921E')
        for fpr, key in keys.iteritems():
            for u, uid in key.uids.iteritems():
                self.assertIsInstance(uid, OpenPGPuid)
                if userid == uid.uid:
                    found = True
                    break
        self.assertTrue(found, "that we can find the userid before removing it")
        self.assertTrue(self.gpg.del_uid(fpr, userid))
        for fpr, key in self.gpg.get_keys('7B75921E').iteritems():
            for u, uid in key.uids.iteritems():
                self.assertNotEqual(userid, uid.uid)

    def test_del_uid_except(self):
        """see if we can easily delete all uids except a certain one"""
        self.assertTrue(self.gpg.import_data(open(os.path.dirname(__file__) + '/7B75921E.asc').read()))
        userid = 'Antoine Beaupré <anarcat@orangeseeds.org>'
        keys = self.gpg.get_keys('7B75921E')
        todelete = []
        # XXX: otherwise test fails with GpgProtocolError: [Errno 0] expected "^\[GNUPG:\] GET_LINE keyedit.prompt", found "gpg: vérification de la base de confiance"
        self.gpg.context.set_option('trust-model', 'always')
        for fpr, key in keys.iteritems():
            for u, uid in key.uids.iteritems():
                if userid != uid.uid:
                    todelete.append(uid.uid)
            for uid in todelete:
                self.gpg.del_uid(fpr, uid)
        for fpr, key in self.gpg.get_keys('7B75921E').iteritems():
            for u, uid in key.uids.iteritems():
                self.assertEqual(userid, uid.uid)

    def test_verify_file(self):
        """test verify_file()"""
        self.assertTrue(self.gpg.verify_file(os.path.dirname(__file__) + '/testfile.txt.asc', os.path.dirname(__file__) + '/testfile.txt'))

class TestKeyringWithAbnormalKeys(TestKeyringBase):
    """this tests specifically weird keys"""
    def setUp(self):
        TestKeyringBase.setUp(self)
        self.assertTrue(self.gpg.import_data(open(os.path.dirname(__file__) + '/96F47C6A.asc').read()))
        self.assertTrue(self.gpg.import_data(open(os.path.dirname(__file__) + '/96F47C6A-secret.asc').read()))

    def test_wrongly_place_sigs(self):
        """this provokes an exception with:

    monkeysign.gpg.GpgProtocolError: [Errno 0] expected "^\[GNUPG:\] GOT_IT", found "gpg: moving a key signature to the correct place"

seems like it's a key not respecting standard: http://lists.nongnu.org/archive/html/sks-devel/2012-07/msg00122.html"""
        self.assertTrue(self.gpg.import_data(open(os.path.dirname(__file__) + '/6D866396.asc').read()))
        self.assertTrue(self.gpg.sign_key('6D866396', True))
        self.gpg.context.call_command(['list-sigs', '6D866396'])
        self.assertRegexpMatches(self.gpg.context.stdout, 'sig:::1:86E4E70A96F47C6A:[^:]*::::Second Test Key <unittests@monkeysphere.info>:10x:')

    def test_broken_encoding(self):
        """test some key that has a non-standard encoding

        RFC4880 specifies that UIDs should be UTF-8, but someone this
        one isn't.

        see https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=736629
        """
        self.assertTrue(self.gpg.import_data(open(os.path.dirname(__file__) +
                                                  '/ECAA37C45C7E48CE.asc').read()))
        key = self.gpg.get_keys('095D9EC8C995AB203DC260FEECAA37C45C7E48CE')
        foo = key['095D9EC8C995AB203DC260FEECAA37C45C7E48CE'].__str__().encode('utf-8')


class TestOpenPGPkey(unittest.TestCase):
    def setUp(self):
        self.key = OpenPGPkey("""tru::1:1343350431:0:3:1:5
pub:-:1024:1:86E4E70A96F47C6A:1342795252:::-:::scESC:
fpr:::::::::3F94240C918E63590B04152E86E4E70A96F47C6A:
uid:-::::1342795252::214CB0EDA28F3CA8754A4D43B7CDB7B114171B3C::Test Key <foo@example.com>:
sub:-:1024:1:894EE34814B46386:1342795252::::::e:""")

    def test_no_dupe_uids(self):
        key = OpenPGPkey()
        self.assertEqual(key.uids, {})

    def test_format_fpr(self):
        expected = '3F94 240C 918E 6359 0B04  152E 86E4 E70A 96F4 7C6A'
        actual = self.key.format_fpr()
        self.assertEqual(expected, actual)

    def test_get_trust(self):
        self.assertEqual('unknown', self.key.get_trust())

class TestSecretOpenPGPkey(unittest.TestCase):
    def setUp(self):
        self.key = OpenPGPkey("""sec::1024:17:586073B34023702F:1110320887:1268438180:::::::::
fpr:::::::::C9E1F1230DBE47D57BAB3C60586073B34023702F:
uid:::::::2451063FCBB4D262938687C2D8F6B949B0A3AF01::The Anarcat <anarcat@anarcat.ath.cx>:
ssb::2048:16:C016FF12EB8D47BB:1110320966::::::::::""")

    def test_print(self):
        print self.key

if __name__ == '__main__':
    unittest.main()
