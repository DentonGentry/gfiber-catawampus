#!/usr/bin/python
# Copyright 2013 Google Inc. All Rights Reserved.
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


"""Handling of ACS configuration."""

__author__ = 'jnewlin@google.com (John Newlin)'

# Refactored from gfmedia.py

import datetime
import errno
import os
import random
import subprocess

import google3

# Unit tests can override these with fake data
CWMP_TMP_DIR = '/tmp/cwmp'
ACSCONTACT = CWMP_TMP_DIR + '/acscontact'
ACSCONNECTED = '/tmp/cwmp/acsconnected'
SET_ACS = 'set-acs'


class AcsConfig(object):
  """Configuration for the ACS.

  This package relies on an external tool 'set-acs' to control the
  configuration of the ACS URL.  A version of the set-acs tool is included
  with the cwmpd software.  If a vendor wants to modify how ACS handling is
  done, modifying the set-acs script is the best place to do that.
  """

  def GetAcsUrl(self):
    """Return the current ACS_URL."""
    setacs = subprocess.Popen([SET_ACS, 'print'], stdout=subprocess.PIPE)
    out, _ = setacs.communicate(None)
    return setacs.returncode == 0 and out.strip() or ''

  def SetAcsUrl(self, url):
    """Called for a SetParameterValue of DeviceInfo.ManagementServer.URL.

    Args:
      url: the URL to set

    Raises:
      AttributeError: If the set-acs command fails.
    """
    set_acs_url = url.strip() or 'clear'
    rc = subprocess.call(args=[SET_ACS, 'cwmp', set_acs_url])
    if rc != 0:
      raise AttributeError('set-acs failed')

  def _BlessAcsUrl(self, url):
    set_acs_url = url.strip() or 'clear'
    rc = subprocess.call(args=[SET_ACS, 'bless', set_acs_url])
    if rc != 0:
      raise AttributeError('set-acs failed')

  def InvalidateAcsUrl(self, url):
    """Removes the given URL from the set of ACS urls to choose from.

    Args:
      url: The URL to invalidate.

    A URL may be found to be invalid if it doesn't match the restrict list.
    For example, if the restrict list is set to '.foo.com' and the url
    returned from GetAcsUrl is 'xxx.bar.com', the then InvalidateAcsUrl will
    be called, and the platform code has a chance to return a different URL.
    This can happen if for example the DHCP server is misconfigured, and
    points to a server/domain that is not on the restrict list, and give the
    platform code a chance to return a default URL, or a URL gotten by some
    other means.

    Returns:
      True: On success.
      False: If there was an error invalidating.
    """
    try:
      subprocess.check_call(args=[SET_ACS, 'timeout', url.strip()])
    except subprocess.CalledProcessError:
      return False
    return True

  def AcsAccessAttempt(self, url):
    """Called before attempting to initiate a connection with the ACS.

    Args:
      url: the ACS_URL being contacted.
    """
    # We only *need* to create a 0 byte file, but write URL for debugging
    with open(ACSCONTACT, 'w') as f:
      f.write(url)

  def AcsAccessSuccess(self, url):
    """Called at the end of every successful ACS session.

    Args:
      url: the ACS_URL being contacted.
    """
    # We only *need* to create a 0 byte file, but write URL for debugging
    with open(ACSCONNECTED, 'w') as f:
      f.write(url)
    self._BlessAcsUrl(url)
