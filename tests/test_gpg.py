import sys, os, shutil
import unittest
import tempfile

sys.path.append(os.path.dirname(__file__) + '/..')

from monkeysign import Gpg, GpgTemp, OpenPGPkey, OpenPGPuid

class TestGpgPlain(unittest.TestCase):
    def test_plain(self):
        g = Gpg()
        self.assertNotIn('homedir', g.options)

class TestGpgTmp(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="monkeysign-")
        self.gpgtmp = Gpg(self.tmp)
        self.assertEqual(self.gpgtmp.options['homedir'], self.tmp)

    def test_home(self):
        self.gpgtmp.export_data('') # dummy call to make gpg populate his directory
        self.assertTrue(open(self.tmp + '/pubring.gpg'))

    def tearDown(self):
        shutil.rmtree(self.tmp)

class TestGpg(unittest.TestCase):
    # those need to match the options in the Gpg class
    options = { 'status-fd': 1,
                'command-fd': 0,
                'no-tty': None,
                'use-agent': None,
                'with-colons': None,
                'with-fingerprint': None,
                'fixed-list-mode': None,
                'list-options': 'show-sig-subpackets,show-uid-validity,show-unusable-uids,show-unusable-subkeys,show-keyring,show-sig-expire',
                }

    # ... and this is the rendered version of the above
    rendered_options = ['gpg', '--command-fd', '0', '--fixed-list-mode', '--with-fingerprint', '--list-options', 'show-sig-subpackets,show-uid-validity,show-unusable-uids,show-unusable-subkeys,show-keyring,show-sig-expire', '--use-agent', '--no-tty', '--with-colons', '--status-fd', '1' ]

    def setUp(self):
        # we test using the temporary keyring because it's too dangerous otherwise
        self.gpg = GpgTemp()
        self.assertIn('homedir', self.gpg.options)

    def test_set_option(self):
        self.gpg.set_option('armor')
        self.assertIn('armor', self.gpg.options)
        self.gpg.set_option('keyserver', 'foo.example.com')
        self.assertDictContainsSubset({'keyserver': 'foo.example.com'}, self.gpg.options)

    def test_build_command(self):
        c1 = self.gpg.build_command(['list-keys', 'foo'])
        self.assertIn('homedir', self.gpg.options)
        c2 = self.rendered_options + ['--list-keys', 'foo'] + ['--homedir', self.gpg.options['homedir']]
        self.assertItemsEqual(c1, c2)

    def test_command(self):
        c = list(self.rendered_options) # work on a copy
        c2 = self.gpg.build_command(['version'])
        c += ['--homedir', self.gpg.options['homedir'], '--version']
        self.assertEqual(c, c2)
        c = list(self.rendered_options)
        c2 = self.gpg.build_command(['export', 'foo'])
        c += ['--homedir', self.gpg.options['homedir'], '--export', 'foo']
        self.assertEqual(c, c2)

    def test_version(self):
        self.assertTrue(self.gpg.version())

    def test_import(self):
        self.assertTrue(self.gpg.import_data(open(os.path.dirname(__file__) + '/96F47C6A.asc').read()))

    def test_import_fail(self):
        self.assertFalse(self.gpg.import_data(''))

    def test_export(self):
        self.assertTrue(self.gpg.import_data(open(os.path.dirname(__file__) + '/96F47C6A.asc').read()))
        k1 = open(os.path.dirname(__file__) + '/96F47C6A.asc').read()
        self.gpg.set_option('armor')
        self.gpg.set_option('export-options', 'export-minimal')
        k2 = self.gpg.export_data('96F47C6A')
        self.assertEqual(k1,k2)

    def test_get_keys(self):
        #k1 = OpenPGPKey()
        #k1.fingerprint = '8DC901CE64146C048AD50FBB792152527B75921E'
        #k1.secret = False
        # just a cute display for now
        self.assertTrue(self.gpg.import_data(open(os.path.dirname(__file__) + '/7B75921E.asc').read()))
        for fpr, key in self.gpg.get_keys('8DC901CE64146C048AD50FBB792152527B75921E').iteritems():
            print key

    def test_get_secret_keys(self):
        self.assertTrue(self.gpg.import_data(open(os.path.dirname(__file__) + '/7B75921E.asc').read()))
        # this shouldn't show anything, as this is just a public key blob
        self.assertFalse(self.gpg.get_keys('8DC901CE64146C048AD50FBB792152527B75921E', True, False))

    def test_export_secret(self):
        self.assertTrue(self.gpg.import_data(open(os.path.dirname(__file__) + '/96F47C6A-secret.asc').read()))
        self.secret = self.gpg.export_data('96F47C6A', True)
        self.assertTrue(self.secret)

    def test_empty_keyring(self):
        """a test should work on an empty keyring

        this is also a test of exporting an empty keyring"""
        self.assertEqual(self.gpg.export_data(), '')

    def test_sign_key_wrong_user(self):
        self.assertTrue(self.gpg.import_data(open(os.path.dirname(__file__) + '/7B75921E.asc').read()))
        self.assertTrue(self.gpg.import_data(open(os.path.dirname(__file__) + '/96F47C6A.asc').read()))
        self.assertTrue(self.gpg.import_data(open(os.path.dirname(__file__) + '/96F47C6A-secret.asc').read()))
        self.gpg.set_option('local-user', '0000000F')
        self.assertFalse(self.gpg.sign_key('7B75921E'))
        for fpr, key in self.gpg.get_keys('7B75921E').iteritems():
            print key

    def test_sign_key(self):
        self.assertTrue(self.gpg.import_data(open(os.path.dirname(__file__) + '/7B75921E.asc').read()))
        self.assertTrue(self.gpg.import_data(open(os.path.dirname(__file__) + '/96F47C6A.asc').read()))
        self.assertTrue(self.gpg.import_data(open(os.path.dirname(__file__) + '/96F47C6A-secret.asc').read()))
        self.assertTrue(self.gpg.sign_key('7B75921E'))
        self.assertNotEqual(self.gpg.stdout, '')
        for fpr, key in self.gpg.get_keys('7B75921E').iteritems():
            print key
        self.gpg.call_command(['list-sigs', '7B75921E'])
        self.assertRegexpMatches(self.gpg.stdout, 'sig:::1:86E4E70A96F47C6A:[^:]*::::Test Key <foo@example.com>:10x:')

    def test_sign_key_missing_key(self):
        """try to sign a missing key

        this should fail because we don't have the public key material
        for the requested key

        however, gpg returns the wrong exit code here, so we end up at
        looking if there is really no output
        """
        self.assertTrue(self.gpg.import_data(open(os.path.dirname(__file__) + '/96F47C6A-secret.asc').read()))
        self.assertTrue(self.gpg.sign_key('7B75921E'))
        self.assertEqual(self.gpg.stdout, '')
        self.assertEqual(self.gpg.stderr, '')

    def test_sign_key_as_user(self):
        """normal signature with a signing user specified"""
        self.assertTrue(self.gpg.import_data(open(os.path.dirname(__file__) + '/7B75921E.asc').read()))
        self.assertTrue(self.gpg.import_data(open(os.path.dirname(__file__) + '/96F47C6A.asc').read()))
        self.assertTrue(self.gpg.import_data(open(os.path.dirname(__file__) + '/96F47C6A-secret.asc').read()))
        self.gpg.set_option('local-user', '96F47C6A')
        self.assertTrue(self.gpg.sign_key('7B75921E'))

    def test_gen_key(self):
        #self.fpr = self.gpg.gen_key()
        #self.assertTrue(self.fpr)
        pass

    def tearDown(self):
        del self.gpg

class TestGpgCaff(unittest.TestCase):
    def setUp(self):
        self.gpgtmp = GpgTemp()

    def test_sign_key_from_other(self):
        gpg = Gpg()
        gpg.set_option('export-options', 'export-minimal')
        self.assertTrue(self.gpgtmp.import_data(gpg.export_data('8DC901CE64146C048AD50FBB792152527B75921E')))
        self.assertTrue(self.gpgtmp.import_data(open(os.path.dirname(__file__) + '/96F47C6A.asc').read()))
        self.assertTrue(self.gpgtmp.import_data(open(os.path.dirname(__file__) + '/96F47C6A-secret.asc').read()))
        self.assertTrue(self.gpgtmp.sign_key('7B75921E'))
        self.gpgtmp.set_option('armor')
        export = self.gpgtmp.export_data('7B75921E')
        print export
        self.assertTrue(export)
        del gpg

    def tearDown(self):
        del self.gpgtmp

class TestOpenPGPkey(unittest.TestCase):
    def setUp(self):
        self.key = OpenPGPkey()

    def test_no_dupe_uids(self):
        self.key.uids[''] = OpenPGPuid('foo@example.com', 'u')
        key = OpenPGPkey()
        self.assertEqual(key.uids, {})

class TestGpgNetwork(unittest.TestCase):
    """Seperate test cases for functions that hit the network"""

    def setUp(self):
        self.gpg = GpgTemp()

    def test_fetch_keys(self):
        self.gpg.set_option('keyserver', 'pool.sks-keyservers.net')
        self.assertTrue(self.gpg.fetch_keys('4023702F'))

    def tearDown(self):
        del self.gpg

if __name__ == '__main__':
    unittest.main()
