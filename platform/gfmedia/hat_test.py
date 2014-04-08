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

"""Unit tests for gfibertv.py."""

__author__ = 'irinams@google.com (Irina Stanescu)'

import os
import os.path
import shutil
import tempfile
import unittest
import google3
import tr.cwmpdate
import tr.helpers
import tr.mainloop
import hat


class HatTests(unittest.TestCase):
  """Tests for hat.py."""

  def setUp(self):
    self.loop = tr.mainloop.MainLoop()
    self.tmpdir = tempfile.mkdtemp()
    hat.SYSTEMPROPS[0] = self.CreateTempFile('systemprops')
    hat.CONTRACTS[0] = self.CreateTempFile('contracts')

  def CreateTempFile(self, name):
    file_name = os.path.join(self.tmpdir, name)
    f = open(file_name, 'w+')
    f.close()
    return file_name

  def tearDown(self):
    shutil.rmtree(self.tmpdir)

  def testValidateExports(self):
    hat_handler = hat.Hat()
    hat_handler.ValidateExports()

  def testSetPartial(self):
    hat_handler = hat.Hat()
    self.loop.RunOnce()
    lines = open(hat.SYSTEMPROPS[0]).readlines()
    self.assertEqual(len(lines), 0)

    hat_handler.HAT = True
    self.loop.RunOnce()
    lines = open(hat.SYSTEMPROPS[0]).readlines()
    self.assertEqual(len(lines), 1)
    self.assertTrue('hat=1\n' in lines)

    hat_handler.Insert = True
    self.loop.RunOnce()
    lines = open(hat.SYSTEMPROPS[0]).readlines()
    self.assertEqual(len(lines), 2)
    self.assertTrue('hat=1\n' in lines)
    self.assertTrue('hat_insertion=1\n' in lines)

  def testSetAll(self):
    hat_handler = hat.Hat()
    hat_handler.HAT = True
    hat_handler.DVRReplacement = False
    hat_handler.Insert = False
    hat_handler.TestCueTones = True
    hat_handler.AFillPercent = 10
    hat_handler.HTFillPercent = 90
    hat_handler.SwapoutSecs = 120
    hat_handler.GFTSPollingIntervalSecs = 1200
    hat_handler.GFTSUrl = 'www.google.com'
    hat_handler.GFASUrl = 'fiber.google.com'

    self.loop.RunOnce()
    lines = open(hat.SYSTEMPROPS[0]).readlines()
    self.assertEqual(len(lines), 10)
    self.assertTrue('hat=1\n' in lines)
    self.assertTrue('hat_insertion=0\n' in lines)
    self.assertTrue('dvr_replacement=0\n' in lines)
    self.assertTrue('test_cue_tones=1\n' in lines)
    self.assertTrue('a_fill_percent=10\n' in lines)
    self.assertTrue('ht_fill_percent=90\n' in lines)
    self.assertTrue('hat_swapout_secs=120\n' in lines)
    self.assertTrue('gfts_polling_interval_secs=1200\n' in lines)
    self.assertTrue('gfas_url=fiber.google.com\n' in lines)
    self.assertTrue('gfts_url=www.google.com\n' in lines)

    hat_handler.HAT = False
    hat_handler.Insert = True
    hat_handler.GFTSPollingIntervalSecs = 12000

    self.loop.RunOnce()
    lines = open(hat.SYSTEMPROPS[0]).readlines()
    self.assertTrue('hat=0\n' in lines)
    self.assertTrue('hat_insertion=1\n' in lines)
    self.assertTrue('dvr_replacement=0\n' in lines)
    self.assertTrue('test_cue_tones=1\n' in lines)
    self.assertTrue('a_fill_percent=10\n' in lines)
    self.assertTrue('ht_fill_percent=90\n' in lines)
    self.assertTrue('hat_swapout_secs=120\n' in lines)
    self.assertTrue('gfts_polling_interval_secs=12000\n' in lines)
    self.assertTrue('gfas_url=fiber.google.com\n' in lines)
    self.assertTrue('gfts_url=www.google.com\n' in lines)

  def testTarget(self):
    hat_handler = hat.Hat()
    hat.USERPROPS[0] = 'testdata/hat/userprops_true'

    self.assertEqual(hat_handler.Target, True);

    hat.USERPROPS[0] = 'testdata/hat/userprops_false'
    self.assertEqual(hat_handler.Target, False);

    hat.USERPROPS[0] = '/blabla/nonexistant'
    self.assertEqual(hat_handler.Target, None);

    hat.USERPROPS[0] = 'testdata/hat/userprops_bad'
    self.assertEqual(hat_handler.Target, None);

  def testContracts(self):
    hat_handler = hat.Hat()
    self.loop.RunOnce()
    self.assertEqual('', hat_handler.HATContracts)

    contracts_file_content = 'testcontent'
    hat_handler.HATContracts = contracts_file_content
    self.loop.RunOnce()
    self.assertEqual(open(hat.CONTRACTS[0]).read(), contracts_file_content + '\n')
    contracts_file_content = 'testcontent2'
    hat_handler.HATContracts = contracts_file_content
    self.loop.RunOnce()
    self.assertEqual(open(hat.CONTRACTS[0]).read(), contracts_file_content + '\n')

if __name__ == '__main__':
  unittest.main()
