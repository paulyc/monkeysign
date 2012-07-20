import sys, os
import unittest

sys.path.append(os.path.dirname(__file__) + '/..')

from monkeysign import Gpg, GpgTemp

class TestGpg(unittest.TestCase):
    def setUp(self):
        self.gpg = Gpg()

    def test_env(self):
        self.gpg = Gpg('/tmp/gpg-home')
        self.assertEqual(os.environ['GPG_HOME'], '/tmp/gpg-home')

    def test_command(self):
        c = self.gpg.build_command([])
        c.append('--version')
        c2 = self.gpg.build_command(['--version'])
        self.assertEqual(c, c2)

    def test_version(self):
        self.assertTrue(self.gpg.version())

class TestGpgTemp(unittest.TestCase):

    def setUp(self):
        self.gpg = GpgTemp()
        
    def test_cleanup(self):
        self.assertTrue(os.path.exists(os.environ['GPG_HOME']))

if __name__ == '__main__':
    unittest.main()
