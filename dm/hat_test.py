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
import google3
import hat
import tr.cwmpdate
import tr.handle
import tr.helpers
import tr.mainloop
from tr.wvtest import unittest


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
    tr.handle.ValidateExports(hat_handler)

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
    hat_handler.MinChannelDwellTimeSecs = 30
    hat_handler.DiskSpaceLowWatermarkPercent = 75
    self.loop.RunOnce()
    lines = open(hat.SYSTEMPROPS[0]).readlines()
    self.assertEqual(len(lines), 4)
    self.assertTrue('hat=1\n' in lines)
    self.assertTrue('hat_insertion=1\n' in lines)
    self.assertTrue('min_channel_dwell_time_secs=30\n' in lines)
    self.assertTrue('disk_space_low_watermark_percent=75\n' in lines)

  def testSetAll(self):
    hat_handler = hat.Hat()
    hat_handler.HAT = True
    hat_handler.DVRReplacement = False
    hat_handler.Insert = False
    hat_handler.TestCueTones = True
    hat_handler.HatRequestMaxDelaySecs = 120
    hat_handler.MinChannelDwellTimeSecs = 10
    hat_handler.MinRepeatHatReportIntervalSecs = 7200
    hat_handler.MinActiveViewingHeuristicSecs = 3600
    hat_handler.DiskSpaceLimitGb = 60
    hat_handler.DiskSpaceLowWatermarkPercent = 50
    hat_handler.DiskSpaceHighWatermarkPercent = 70
    hat_handler.DiskSpaceCleanupIntervalSecs = 180
    hat_handler.HatCatalogPollingIntervalSecs = 600
    hat_handler.AdFetchMaxLeadTimeSecs = 0
    hat_handler.AdCreativeGracePeriodSecs = 0
    hat_handler.MinImpressionViewDurationPts = 450000
    hat_handler.CueToneFiredAdRequests = True
    hat_handler.FrameAccurateSplicing = False
    throttle = '[00:00-6:00,25,15][12:00-6:00,25,40]'
    hat_handler.FetcherThrottlingIntervals = throttle
    hat_handler.GFASUrl = 'fiber.google.com'
    hat_handler.AdscaleMulticastAddress = '224.1.2.3:12345'
    hat_handler.InteractiveAds = False

    self.loop.RunOnce()
    lines = open(hat.SYSTEMPROPS[0]).readlines()
    expected = ['hat=1\n',
                'hat_insertion=0\n',
                'dvr_replacement=0\n',
                'test_cue_tones=1\n',
                'hat_request_max_delay_secs=120\n',
                'min_channel_dwell_time_secs=10\n',
                'min_repeat_hat_report_interval_secs=7200\n',
                'min_active_viewing_heuristic_secs=3600\n',
                'disk_space_limit_gb=60\n',
                'disk_space_low_watermark_percent=50\n',
                'disk_space_high_watermark_percent=70\n',
                'disk_space_cleanup_interval_secs=180\n',
                'hat_catalog_polling_interval_secs=600\n',
                'ad_fetch_max_lead_time_secs=0\n',
                'ad_creative_grace_period_secs=0\n',
                'min_impression_view_duration_pts=450000\n',
                'cue_tone_fired_ad_requests=1\n',
                'frame_accurate_splicing=0\n',
                'fetcher_throttling_intervals='
                '[00:00-6:00,25,15][12:00-6:00,25,40]\n',
                'gfas_url=fiber.google.com\n',
                'adscale_multicast_address=224.1.2.3:12345\n',
                'interactive_ads=0\n',
               ]
    for ex in expected:
      self.assertTrue(ex in lines)
      lines.remove(ex)
    self.assertEqual(0, len(lines))

    hat_handler.HAT = False
    hat_handler.Insert = True
    hat_handler.MinRepeatHatReportIntervalSecs = 600
    hat_handler.AdFetchMaxLeadTimeSecs = 3601
    hat_handler.AdCreativeGracePeriodSecs = 42
    hat_handler.DiskSpaceHighWatermarkPercent = 90
    hat_handler.CueToneFiredAdRequests = False
    hat_handler.FrameAccurateSplicing = True
    hat_handler.FetcherThrottlingIntervals = '[00:00-6:00,10,25]'
    hat_handler.AdscaleMulticastAddress = '224.1.2.3:12345'
    hat_handler.InteractiveAds = True

    self.loop.RunOnce()
    lines = open(hat.SYSTEMPROPS[0]).readlines()
    self.assertTrue('hat=0\n' in lines)
    self.assertTrue('hat_insertion=1\n' in lines)
    self.assertTrue('dvr_replacement=0\n' in lines)
    self.assertTrue('test_cue_tones=1\n' in lines)
    self.assertTrue('hat_request_max_delay_secs=120\n' in lines)
    self.assertTrue('min_channel_dwell_time_secs=10\n' in lines)
    self.assertTrue('min_repeat_hat_report_interval_secs=600\n' in lines)
    self.assertTrue('min_active_viewing_heuristic_secs=3600\n' in lines)
    self.assertTrue('disk_space_limit_gb=60\n' in lines)
    self.assertTrue('disk_space_low_watermark_percent=50\n' in lines)
    self.assertTrue('disk_space_high_watermark_percent=90\n' in lines)
    self.assertTrue('disk_space_cleanup_interval_secs=180\n' in lines)
    self.assertTrue('hat_catalog_polling_interval_secs=600\n' in lines)
    self.assertTrue('ad_fetch_max_lead_time_secs=3601\n' in lines)
    self.assertTrue('ad_creative_grace_period_secs=42\n' in lines)
    self.assertTrue('min_impression_view_duration_pts=450000\n' in lines)
    self.assertTrue('cue_tone_fired_ad_requests=0\n' in lines)
    self.assertTrue('frame_accurate_splicing=1\n' in lines)
    self.assertTrue('fetcher_throttling_intervals='
                    '[00:00-6:00,10,25]\n' in lines)
    self.assertTrue('gfas_url=fiber.google.com\n' in lines)
    self.assertTrue('adscale_multicast_address=224.1.2.3:12345\n' in lines)
    self.assertTrue('interactive_ads=1\n' in lines)

  def testContracts(self):
    hat_handler = hat.Hat()
    self.loop.RunOnce()
    self.assertEqual('', hat_handler.HATContracts)

    contracts_file_content = 'testcontent'
    hat_handler.HATContracts = contracts_file_content
    self.loop.RunOnce()
    self.assertEqual(
        open(hat.CONTRACTS[0]).read(), contracts_file_content + '\n')
    contracts_file_content = 'testcontent2'
    hat_handler.HATContracts = contracts_file_content
    self.loop.RunOnce()
    self.assertEqual(
        open(hat.CONTRACTS[0]).read(), contracts_file_content + '\n')

  def testNoDirectory(self):
    hat.SYSTEMPROPS[0] = '/no/such/directory/systemprops'
    hat_handler = hat.Hat()
    hat_handler.HatRequestMaxDelaySecs = 120
    self.loop.RunOnce()
    # just checking that there is no exception


if __name__ == '__main__':
  unittest.main()
