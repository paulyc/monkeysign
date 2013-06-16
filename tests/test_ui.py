#!/usr/bin/pytho
# -*- coding: utf-8 -*-

"""
Test suite for the basic user interface class.
"""

import unittest
import os
import sys

sys.path.append(os.path.dirname(__file__) + '/..')

from monkeysign.ui import MonkeysignUi

class BasicTests(unittest.TestCase):
    def setUp(self):
        (options, args) = MonkeysignUi.parse_args()
        options.dryrun = True
        options.nomail = True
        self.ui = MonkeysignUi(options, None)
        self.tmphomedir = self.ui.tmpkeyring.tmphomedir

    def test_cleanup(self):
        del self.ui
        self.assertFalse(os.path.exists(self.tmphomedir))
