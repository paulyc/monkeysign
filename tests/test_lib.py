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

"""
Library of test tools that can be reused across different test suites.
"""

import signal
import time
import unittest

class AlarmException(IOError):
    pass

def handle_alarm(signum, frame):
    raise AlarmException('timeout in %s' % frame.f_code.co_name)

class TestTimeLimit(unittest.TestCase):
    """a test with a timeout"""

    # in seconds
    timeout = 3

    def setUp(self):
        signal.signal(signal.SIGALRM, handle_alarm)
        signal.setitimer(signal.ITIMER_REAL, self.timeout)

    def tearDown(self):
        signal.alarm(0)

class TestTimeLimitSelfTest(TestTimeLimit):

    # 10ms
    timeout = 0.01

    def test_signal(self):
        with self.assertRaises(AlarmException):
            time.sleep(1)

if __name__ == '__main__':
    unittest.main()
