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
        self.gpg.context.set_option('keyserver', 'pool.sks-keyservers.net')

    def test_fetch_keys(self):
        self.assertTrue(self.gpg.fetch_keys('4023702F'))

    def test_special_key(self):
        """test a key that sign_key had trouble with"""
        self.assertTrue(self.gpg.import_data(open(os.path.dirname(__file__) + '/96F47C6A.asc').read()))
        self.assertTrue(self.gpg.import_data(open(os.path.dirname(__file__) + '/96F47C6A-secret.asc').read()))
        self.assertTrue(self.gpg.fetch_keys('3CCDBB7355D1758F549354D20B123309D3366755'))
        self.assertTrue(self.gpg.sign_key('3CCDBB7355D1758F549354D20B123309D3366755'))

    def tearDown(self):
        del self.gpg

if __name__ == '__main__':
    unittest.main()
