#!/usr/bin/python
# Copyright 2014 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# unittest requires method names starting in 'test'
#pylint: disable-msg=C6409

"""Unit tests for catawampus.py implementation."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import google3
from tr.wvtest import unittest
import catawampus


class CatawampusTest(unittest.TestCase):
  """Tests for catawampus.py."""

  def testValidateExports(self):
    c = catawampus.CatawampusDm()
    c.ValidateExports()

  def testRuntimeEnv(self):
    c = catawampus.CatawampusDm()
    self.assertTrue(c.RuntimeEnvInfo)

  def testProfiler(self):
    c = catawampus.CatawampusDm()
    c.Profiler.Enable = True
    # Profiler is running. Need something to profile.
    j = 0
    for i in range(1000):
      j += i
    c.Profiler.Enable = False
    # We don't check the content (too fragile for a test), just that it
    # generated *something*
    self.assertTrue(c.Profiler.Result)


if __name__ == '__main__':
  unittest.main()
