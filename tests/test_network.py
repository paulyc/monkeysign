#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Tests that hit the network.

Those tests are in a seperate file to allow the base set of tests to
be ran without internet access.
"""

import unittest

import sys, os
sys.path.append(os.path.dirname(__file__) + '/..')

from gpg import TempKeyring

class TestGpgNetwork(unittest.TestCase):
    """Seperate test cases for functions that hit the network"""

    def setUp(self):
        self.gpg = TempKeyring()

    def test_fetch_keys(self):
        self.gpg.set_option('keyserver', 'pool.sks-keyservers.net')
        self.assertTrue(self.gpg.fetch_keys('4023702F'))

    def tearDown(self):
        del self.gpg

if __name__ == '__main__':
    unittest.main()
