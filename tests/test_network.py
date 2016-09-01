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

"""Tests that hit the network.

Those tests are in a separate file to allow the base set of tests to
be ran without internet access.
"""

import unittest

import sys, os
import signal
sys.path.insert(0, os.path.dirname(__file__) + '/..')

from monkeysign.gpg import TempKeyring
from test_lib import TestTimeLimit, AlarmException

class TestGpgNetwork(TestTimeLimit):
    """Separate test cases for functions that hit the network

each test needs to run under a specific timeout so we don't wait on
the network forever"""

    def setUp(self):
        self.gpg = TempKeyring()
        self.gpg.context.set_option('keyserver', 'pool.sks-keyservers.net')
        TestTimeLimit.setUp(self)

    def test_fetch_keys(self):
        """test key fetching from keyservers"""
        try:
            self.assertTrue(self.gpg.fetch_keys('4023702F'))
        except AlarmException:
            raise unittest.case._ExpectedFailure(sys.exc_info())

    def test_special_key(self):
        """test a key that sign_key had trouble with"""
        self.assertTrue(self.gpg.import_data(open(os.path.dirname(__file__) + '/96F47C6A.asc').read()))
        self.assertTrue(self.gpg.import_data(open(os.path.dirname(__file__) + '/96F47C6A-secret.asc').read()))
        try:
            self.assertTrue(self.gpg.fetch_keys('3CCDBB7355D1758F549354D20B123309D3366755'))
        except AlarmException:
            raise unittest.case._ExpectedFailure(sys.exc_info())
        self.assertTrue(self.gpg.sign_key('3CCDBB7355D1758F549354D20B123309D3366755', True))

    def tearDown(self):
        TestTimeLimit.tearDown(self)
        del self.gpg

if __name__ == '__main__':
    unittest.main()
