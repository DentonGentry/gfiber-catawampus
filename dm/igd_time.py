#!/usr/bin/python
# Copyright 2012 Google Inc. All Rights Reserved.
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

"""Implementation of tr-98 InternetGatewayDevice.Time.
"""

__author__ = 'dgentry@google.com (Denton Gentry)'

import datetime

import os
import re
import struct
import tr.basemodel
import tr.cwmpdate
import tr.helpers
import tr.cwmptypes


BASE98IGD = tr.basemodel.InternetGatewayDevice
LOCALTIMEFILE = '/tmp/localtime'
TIMENOW = datetime.datetime.now
TIMESYNCEDFILE = '/tmp/time.synced'
TZFILE = '/tmp/TZ'


class TimeTZ(BASE98IGD.Time):
  """An implementation of tr98 InternetGatewayDevice.Time.

  Timezones in this system are POSIX TZ strings like
  'PST8PDT,M3.2.0,M11.1.0'. The timezone is written to
  two places:
    /tmp/TZ as a simple string, where it is used by ucLibc and SageTV
    /tmp/localtime in tzfile format, where it is used by glibc
  The rootfs is generally a squashfs with softlinks in /etc
  pointing to /tmp/TZ and /tmp/localtime.
  """

  Enable = tr.cwmptypes.ReadOnlyBool(True)

  def __init__(self):
    super(TimeTZ, self).__init__()
    self.Unexport(['DaylightSavingsEnd', 'DaylightSavingsStart',
                   'DaylightSavingsUsed', 'LocalTimeZone', 'NTPServer1',
                   'NTPServer2', 'NTPServer3', 'NTPServer4', 'NTPServer5'])
    self.new_local_time_zone_name = ''

  @property
  def CurrentLocalTime(self):
    return tr.cwmpdate.format(TIMENOW())

  def GetLocalTimeZoneName(self):
    try:
      return open(TZFILE).readline().strip()
    except IOError:
      return ''

  def SetLocalTimeZoneName(self, value):
    self.new_local_time_zone_name = str(value)
    self.WriteTimezone()

  LocalTimeZoneName = property(GetLocalTimeZoneName, SetLocalTimeZoneName, None,
                               'InternetGatewayDevice.Time.LocalTimeZoneName')

  @property
  def Status(self):
    if os.path.exists(TIMESYNCEDFILE):
      return 'Synchronized'
    return 'Unsynchronized'

  def _PosixTZtoTzfile(self, tz):
    """Convert a POSIX TZ string to a glibc tzfile.

    Args:
      tz: a string of the form 'PST8PDT,M3.2.0,M11.1.0'

    Returns:
      http://manpages.ubuntu.com/manpages/quantal/man5/tzfile.5.html
    """
    (abbrev, hours, _) = re.split(r'(\d+)', tz, 1)
    offset = int(hours) * 60 * 60 * -1
    # glibc ignores the TZ string if there are no dst transitions in the
    # regular tzfile so we provide exactly one, at 0xCB6970 seconds from
    # the epoch (which is June 4, 1970).
    thunk32 = struct.pack('>4sc15x6IIBi2x4s', 'TZif', '2', 0, 0, 0, 1, 1, 4,
                          0xCB6970, 0, offset, abbrev)
    thunk64 = struct.pack('>4sc15x6IQBi2x4s', 'TZif', '2', 0, 0, 0, 1, 1, 4,
                          0xCB6970, 0, offset, abbrev)
    newlinetz = '\n%s\n' % tz.strip()
    return thunk32 + thunk64 + newlinetz

  @tr.mainloop.WaitUntilIdle
  def WriteTimezone(self):
    try:
      tzfile = self._PosixTZtoTzfile(self.new_local_time_zone_name)
      tr.helpers.WriteFileAtomic(LOCALTIMEFILE, tzfile)
      # uClibc picky about whitespace: exactly one newline, no more, no less.
      tz = self.new_local_time_zone_name.strip() + '\n'
      tr.helpers.WriteFileAtomic(TZFILE, tz)
    except ValueError:
      print 'Unable to write timezone files'
    self.new_local_time_zone_name = ''
