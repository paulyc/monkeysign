#!/usr/bin/python
# -*- coding: utf-8 -*-

"""General test suite for the GPG API.

Tests that require network access should go in test_network.py.
"""

import sys, os, shutil
from StringIO import StringIO
import unittest
import tempfile

sys.path.append(os.path.dirname(__file__) + '/..')

from gpg import Context, Keyring, TempKeyring, OpenPGPkey, OpenPGPuid, GpgProcotolError

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
        self.assertIn('tmphomedir', self.gpg)

    def tearDown(self):
        del self.gpg

class TestKeyring(unittest.TestCase):
    """Test the Keyring class."""

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
        with self.assertRaises(IOError):
            self.assertFalse(self.gpg.import_data(''))

    def test_export(self):
        """test that we can export data similar to what we import

        @todo this will probably fail if tests are ran on a different GPG version
        """
        self.assertTrue(self.gpg.import_data(open(os.path.dirname(__file__) + '/96F47C6A.asc').read()))
        k1 = open(os.path.dirname(__file__) + '/96F47C6A.asc').read()
        self.gpg.context.set_option('armor')
        self.gpg.context.set_option('export-options', 'export-minimal')
        k2 = self.gpg.export_data('96F47C6A')
        self.assertEqual(k1,k2)

    def test_get_keys(self):
        """test that we can list the keys after importing them

        @todo we should check the data structure
        """
        #k1 = OpenPGPKey()
        #k1.fingerprint = '8DC901CE64146C048AD50FBB792152527B75921E'
        #k1.secret = False
        # just a cute display for now
        self.assertTrue(self.gpg.import_data(open(os.path.dirname(__file__) + '/7B75921E.asc').read()))
        for fpr, key in self.gpg.get_keys('8DC901CE64146C048AD50FBB792152527B75921E').iteritems():
            print key

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

    def test_empty_keyring(self):
        """a test should work on an empty keyring

        this is also a test of exporting an empty keyring"""
        self.assertEqual(self.gpg.export_data(), '')

    def test_sign_key_wrong_user(self):
        """make sure sign_key with a erroneous local-user fails

        that is, even if all other conditions are ok"""
        self.assertTrue(self.gpg.import_data(open(os.path.dirname(__file__) + '/7B75921E.asc').read()))
        self.assertTrue(self.gpg.import_data(open(os.path.dirname(__file__) + '/96F47C6A.asc').read()))
        self.assertTrue(self.gpg.import_data(open(os.path.dirname(__file__) + '/96F47C6A-secret.asc').read()))
        self.gpg.context.set_option('local-user', '0000000F')
        with self.assertRaises(GpgProcotolError):
            self.gpg.sign_key('7B75921E', True)

    def test_sign_key_all_uids(self):
        """test signature of all uids of a key"""
        self.assertTrue(self.gpg.import_data(open(os.path.dirname(__file__) + '/7B75921E.asc').read()))
        self.assertTrue(self.gpg.import_data(open(os.path.dirname(__file__) + '/96F47C6A.asc').read()))
        self.assertTrue(self.gpg.import_data(open(os.path.dirname(__file__) + '/96F47C6A-secret.asc').read()))
        self.assertTrue(self.gpg.sign_key('7B75921E', True))
        self.gpg.context.call_command(['list-sigs', '7B75921E'])
        self.assertRegexpMatches(self.gpg.context.stdout, 'sig:::1:86E4E70A96F47C6A:[^:]*::::Test Key <foo@example.com>:10x:')

    def test_sign_key_uid(self):
        """test signature of a single uid"""
        self.assertTrue(self.gpg.import_data(open(os.path.dirname(__file__) + '/7B75921E.asc').read()))
        self.assertTrue(self.gpg.import_data(open(os.path.dirname(__file__) + '/96F47C6A.asc').read()))
        self.assertTrue(self.gpg.import_data(open(os.path.dirname(__file__) + '/96F47C6A-secret.asc').read()))
        self.assertTrue(self.gpg.sign_key('Antoine Beaupré <anarcat@debian.org>'))
        self.gpg.context.call_command(['list-sigs', '7B75921E'])
        self.assertRegexpMatches(self.gpg.context.stdout, 'sig:::1:86E4E70A96F47C6A:[^:]*::::Test Key <foo@example.com>:10x:')

    def test_sign_key_missing_key(self):
        """try to sign a missing key

        this should fail because we don't have the public key material
        for the requested key

        however, gpg returns the wrong exit code here, so we end up at
        looking if there is really no output
        """
        self.assertTrue(self.gpg.import_data(open(os.path.dirname(__file__) + '/96F47C6A-secret.asc').read()))
        with self.assertRaises(GpgProcotolError):
            self.gpg.sign_key('7B75921E')
            self.assertEqual(self.gpg.context.stdout, '')
            self.assertEqual(self.gpg.context.stderr, '')

    def test_sign_key_as_user(self):
        """normal signature with a signing user specified"""
        self.assertTrue(self.gpg.import_data(open(os.path.dirname(__file__) + '/7B75921E.asc').read()))
        self.assertTrue(self.gpg.import_data(open(os.path.dirname(__file__) + '/96F47C6A.asc').read()))
        self.assertTrue(self.gpg.import_data(open(os.path.dirname(__file__) + '/96F47C6A-secret.asc').read()))
        self.gpg.context.set_option('local-user', '96F47C6A')
        self.assertTrue(self.gpg.sign_key('7B75921E', True))

    def test_sign_already_signed(self):
        """test if signing a already signed key fails with a meaningful message

        @todo not implemented"""
        pass

    def test_encrypt_data_armored_untrusted(self):
        """test if we can encrypt data to our private key (and decrypt it)"""
        self.assertTrue(self.gpg.import_data(open(os.path.dirname(__file__) + '/96F47C6A.asc').read()))

        plaintext = 'i come in peace'
        self.gpg.context.debug = sys.stderr

        self.gpg.context.set_option('always-trust') # evil?
        self.gpg.context.set_option('armor')
        cyphertext = self.gpg.encrypt_data(plaintext, '96F47C6A')
        self.assertTrue(cyphertext)

        self.gpg.context.debug = False
        self.assertTrue(self.gpg.import_data(open(os.path.dirname(__file__) + '/96F47C6A-secret.asc').read()))

        self.gpg.context.call_command(['decrypt'], cyphertext)
        self.assertTrue(self.gpg.context.returncode == 0)
        self.assertEqual(self.gpg.context.stdout, plaintext)

    def test_gen_key(self):
        """test key generation

        not implemented"""
        #self.fpr = self.gpg.gen_key()
        #self.assertTrue(self.fpr)
        pass

class TestOpenPGPkey(unittest.TestCase):
    def setUp(self):
        self.key = OpenPGPkey()

    def test_no_dupe_uids(self):
        self.key.uids[''] = OpenPGPuid('foo@example.com', 'u')
        key = OpenPGPkey()
        self.assertEqual(key.uids, {})

    def test_format_fpr(self):
        self.key.fpr = '3F94240C918E63590B04152E86E4E70A96F47C6A'
        expected = '3F94 240C 918E 6359 0B04  152E 86E4 E70A 96F4 7C6A'
        actual = self.key.format_fpr()
        self.assertEqual(expected, actual)

if __name__ == '__main__':
    unittest.main()
