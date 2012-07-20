import sys, os, shutil
import unittest
import tempfile

sys.path.append(os.path.dirname(__file__) + '/..')

from monkeysign import Gpg, GpgTemp

class TestGpgPlain(unittest.TestCase):
    def test_plain(self):
        g = Gpg()
        self.assertNotIn('homedir', g.options)

class TestGpgTmp(unittest.TestCase):
    def setUp(self):
        self.gpg = Gpg('/tmp/gpg-home')

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
        self.assertTrue(self.gpg.import_data(open(os.path.dirname(__file__) + '/7B75921E.asc').read()))
        for fpr, key in self.gpg.get_keys('8DC901CE64146C048AD50FBB792152527B75921E').iteritems():
            print >>sys.stderr, key

    def test_get_secret_keys(self):
        self.assertTrue(self.gpg.import_data(open(os.path.dirname(__file__) + '/7B75921E.asc').read()))
        # this shouldn't show anything, as this is just a public key blob
        self.assertFalse(self.gpg.get_keys('8DC901CE64146C048AD50FBB792152527B75921E', True, False))

    def test_sign_key(self):
        #self.assertTrue(self.gpg.sign_key('343CA353'))            
        pass

    def test_sign_key_from_other(self):
        gpg = Gpg()
        gpgtmp = Gpg(tempfile.mkdtemp(prefix="monkeysign-"))
        data = gpg.export_data('8DC901CE64146C048AD50FBB792152527B75921E')
        self.assertTrue(data)
        self.assertTrue(gpgtmp.import_data(data))
        self.assertTrue(gpgtmp.import_data(gpg.export_data('343CA353')))
        gpg.set_option('export-secret-keys')
        gpgtmp.import_data(gpg.export_data('8DC901CE64146C048AD50FBB792152527B75921E'))
        gpgtmp.sign_key('343CA353')
        print self.gpg.export_data('343CA353')

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
