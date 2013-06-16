#!/usr/bin/python

import unittest
import sys
import os
import time

sys.path.append(os.path.dirname(__file__))

suite = unittest.TestLoader().discover('tests')
unittest.TextTestRunner().run(suite)
