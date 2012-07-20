import sys, os
import unittest

sys.path.append(os.path.dirname(__file__) + '/..')

from monkeysign import Gpg, GpgTemp

class TestGpgPlain(unittest.TestCase):
    def test_plain(self):
        g = Gpg()
        self.assertNotIn('homedir', g.options)

class TestGpgTmp(unittest.TestCase):
    def setUp(self):
        self.gpg = Gpg('/tmp/gpg-home')

    def test_env(self):
        self.assertEqual(os.environ['GPG_HOME'], '/tmp/gpg-home')

class TestGpgTemp(unittest.TestCase):
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
        if 'GPG_HOME' in os.environ: del os.environ['GPG_HOME']
        # we test using the temporary keyring because it's too dangerous otherwise
        self.gpg = GpgTemp()

    def test_set_option(self):
        self.gpg.set_option('armor')
        self.assertIn('armor', self.gpg.options)
        self.gpg.set_option('keyserver', 'foo.example.com')
        self.assertDictContainsSubset({'keyserver': 'foo.example.com'}, self.gpg.options)

    def test_build_command(self):
        # reset options to a known setting
        self.gpg.options = dict(self.options) # work on a copy
        self.assertItemsEqual(self.gpg.build_command(['list-keys', 'foo']), self.rendered_options + ['--list-keys', 'foo'])

    def test_env(self):
        self.assertTrue(os.path.exists(os.environ['GPG_HOME']))

    def test_command(self):
        c = list(self.rendered_options) # work on a copy
        c.append('--version')
        c2 = self.gpg.build_command(['version'])
        self.assertEqual(c, c2)
        c = list(self.rendered_options)
        c.append('--export')
        c.append('foo')
        c2 = self.gpg.build_command(['export', 'foo'])
        self.assertEqual(c, c2)

    def test_version(self):
        self.assertTrue(self.gpg.version())

    def test_import(self):
        self.assertTrue(self.gpg.import_data(open(os.path.dirname(__file__) + '/7B75921E.asc').read()))

    def test_import_again(self):
        # shouldn't this fail to import the second time?
        self.assertTrue(self.gpg.import_data(open(os.path.dirname(__file__) + '/7B75921E.asc').read()))

    def test_import_fail(self):
        self.assertFalse(self.gpg.import_data(''))

    def test_export(self):
        k1 = open(os.path.dirname(__file__) + '/7B75921E.asc').read()
        self.gpg.set_option('armor')
        self.gpg.set_option('export-options', 'export-minimal')
        k2 = self.gpg.export_data('7B75921E')
        self.assertEqual(k1,k2)

    def test_get_keys(self):
        #k1 = OpenPGPKey()
        #k1.fingerprint = '8DC901CE64146C048AD50FBB792152527B75921E'
        #k1.secret = False
        # just a cute display for now
        for fpr, key in self.gpg.get_keys('8DC901CE64146C048AD50FBB792152527B75921E').iteritems():
            print >>sys.stderr, key

    def test_get_secret_keys(self):
        #k1 = OpenPGPKey()
        #k1.fingerprint = '8DC901CE64146C048AD50FBB792152527B75921E'
        #k1.secret = False
        # just a cute display for now
        for fpr, key in self.gpg.get_keys('8DC901CE64146C048AD50FBB792152527B75921E', True, False).iteritems():
            print >>sys.stderr, key

    def tearDown(self):
        del self.gpg

class TestGpgNetwork(unittest.TestCase):
    """Seperate test cases for functions that hit the network"""

    def setUp(self):
        self.gpg = GpgTemp()

    def test_fetch_keys(self):
        self.assertTrue(self.gpg.fetch_keys('4023702F'))

    def tearDown(self):
        del self.gpg

if __name__ == '__main__':
    unittest.main()
