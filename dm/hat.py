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

# TR-069 has mandatory attribute names that don't comply with policy
# pylint:disable=invalid-name

"""Implement handling for the X_GOOGLE_COM_HAT vendor data model."""

__author__ = 'irinams@google.com (Irina Stanescu)'

import errno
import google3
import tr.cwmptypes
import tr.handle
import tr.helpers
import tr.mainloop
import tr.x_catawampus_tr181_2_0

BASE = tr.x_catawampus_tr181_2_0.X_CATAWAMPUS_ORG_Device_v2_0
CATABASE = BASE.Device.X_CATAWAMPUS_ORG

SYSTEMPROPS = ['/rw/sagesrv/sagesrv.properties']
CONTRACTS = ['/rw/ads/contracts/ad_contracts.csv']


class Hat(CATABASE.HAT):
  """Implementation of x-hat.xml."""
  HAT = tr.cwmptypes.TriggerBool()
  DVRReplacement = tr.cwmptypes.TriggerBool()
  Insert = tr.cwmptypes.TriggerBool()
  TestCueTones = tr.cwmptypes.TriggerBool()
  HatRequestMaxDelaySecs = tr.cwmptypes.TriggerUnsigned()
  MinChannelDwellTimeSecs = tr.cwmptypes.TriggerUnsigned()
  MinRepeatHatReportIntervalSecs = tr.cwmptypes.TriggerUnsigned()
  MinActiveViewingHeuristicSecs = tr.cwmptypes.TriggerUnsigned()
  DiskSpaceLimitGb = tr.cwmptypes.TriggerUnsigned()
  DiskSpaceLowWatermarkPercent = tr.cwmptypes.TriggerUnsigned()
  DiskSpaceHighWatermarkPercent = tr.cwmptypes.TriggerUnsigned()
  DiskSpaceCleanupIntervalSecs = tr.cwmptypes.TriggerUnsigned()
  HatCatalogPollingIntervalSecs = tr.cwmptypes.TriggerUnsigned()
  AdFetchMaxLeadTimeSecs = tr.cwmptypes.TriggerUnsigned()
  MinImpressionViewDurationPts = tr.cwmptypes.TriggerInt()
  CueToneFiredAdRequests = tr.cwmptypes.TriggerBool()
  FrameAccurateSplicing = tr.cwmptypes.TriggerBool()

  GFASUrl = tr.cwmptypes.TriggerString()
  FetcherThrottlingIntervals = tr.cwmptypes.TriggerString()

  HATContracts = tr.cwmptypes.FileBacked(
      CONTRACTS, tr.cwmptypes.String(), delete_if_empty=True,
      file_owner='video', file_group='video')

  def __init__(self):
    super(Hat, self).__init__()

  def printIfSetBool(self, f, var, name):
    if var is not None:
      if var:
        f.write('%s=1\n' % name)
      else:
        f.write('%s=0\n' % name)

  def printIfSetUnsigned(self, f, var, name):
    if var is not None:
      f.write('%s=%d\n' % (name, var))

  def printIfSetSigned(self, f, var, name):
    self.printIfSetUnsigned(f, var, name)

  def printIfSetString(self, f, var, name):
    if var is not None:
      f.write('%s=%s\n' % (name, var))

  def _WriteHatFile(self):
    with tr.helpers.AtomicFile(
        SYSTEMPROPS[0], owner='video', group='video') as f:
      self.printIfSetBool(f, self.HAT, 'hat')
      self.printIfSetBool(f, self.DVRReplacement, 'dvr_replacement')
      self.printIfSetBool(f, self.Insert, 'hat_insertion')
      self.printIfSetBool(f, self.TestCueTones, 'test_cue_tones')
      self.printIfSetUnsigned(f, self.HatRequestMaxDelaySecs,
                              'hat_request_max_delay_secs')
      self.printIfSetUnsigned(f, self.MinChannelDwellTimeSecs,
                              'min_channel_dwell_time_secs')
      self.printIfSetUnsigned(f, self.MinRepeatHatReportIntervalSecs,
                              'min_repeat_hat_report_interval_secs')
      self.printIfSetUnsigned(f, self.MinActiveViewingHeuristicSecs,
                              'min_active_viewing_heuristic_secs')
      self.printIfSetUnsigned(f, self.DiskSpaceLimitGb, 'disk_space_limit_gb')
      self.printIfSetUnsigned(f, self.DiskSpaceLowWatermarkPercent,
                              'disk_space_low_watermark_percent')
      self.printIfSetUnsigned(f, self.DiskSpaceHighWatermarkPercent,
                              'disk_space_high_watermark_percent')
      self.printIfSetUnsigned(f, self.DiskSpaceCleanupIntervalSecs,
                              'disk_space_cleanup_interval_secs')
      self.printIfSetUnsigned(f, self.HatCatalogPollingIntervalSecs,
                              'hat_catalog_polling_interval_secs')
      self.printIfSetUnsigned(f, self.AdFetchMaxLeadTimeSecs,
                              'ad_fetch_max_lead_time_secs')
      self.printIfSetSigned(f, self.MinImpressionViewDurationPts,
                            'min_impression_view_duration_pts')
      self.printIfSetBool(f, self.CueToneFiredAdRequests,
                          'cue_tone_fired_ad_requests')
      self.printIfSetBool(f, self.FrameAccurateSplicing,
                          'frame_accurate_splicing')
      self.printIfSetString(f, self.FetcherThrottlingIntervals,
                            'fetcher_throttling_intervals')
      self.printIfSetString(f, self.GFASUrl, 'gfas_url')

  @tr.mainloop.WaitUntilIdle
  def Triggered(self):
    try:
      self._WriteHatFile()
    except IOError as e:
      if e.errno == errno.ENOENT:
        print 'hat.py: no such file: %s' % SYSTEMPROPS[0]
      else:
        raise

if __name__ == '__main__':
  print tr.handle.DumpSchema(Hat())
