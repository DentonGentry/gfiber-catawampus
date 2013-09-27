#!/usr/bin/python
# Copyright 2011 Google Inc. All Rights Reserved.
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
#pylint: disable-msg=C6409
#pylint: disable-msg=W0404
#
"""Implement the inner handling for tr-98/181 ManagementServer."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import copy
import datetime
import math
import random
import re
import socket
import sys
import time
import urlparse

import google3
import tornado.ioloop
import cwmpbool
import cwmpdate


# Allow unit tests to override with a mock
PERIODIC_CALLBACK = tornado.ioloop.PeriodicCallback
SESSIONTIMEOUTFILE = '/tmp/cwmp/session_timeout'

class ServerParameters(object):
  """Class to hold parameters of CpeManagementServer."""

  def __init__(self):
    self.CWMPRetryMinimumWaitInterval = 5
    self.CWMPRetryIntervalMultiplier = 2000
    # The default password is trivial. In the initial Inform exchange
    # the ACS generally sets ConnectionRequest{Username,Password}
    # to values which only it knows. If something goes wrong, we want
    # the password to be well known so the ACS can wake us up and
    # try again.
    self.ConnectionRequestPassword = 'cwmp'
    self.ConnectionRequestUsername = 'catawampus'
    self.DefaultActiveNotificationThrottle = 0
    self.EnableCWMP = True
    self.PeriodicInformEnable = True
    # Once every 15 minutes plus or minus one minute (3 minute spread)
    self.PeriodicInformInterval = (15 * 60) + random.randint(-60, 60)
    self.PeriodicInformTime = 0
    self.Password = ''
    self.Username = ''


class CpeManagementServer(object):
  """Inner class implementing tr-98 & 181 ManagementServer."""

  def __init__(self, acs_config, port, ping_path,
               acs_url=None, get_parameter_key=None,
               start_periodic_session=None, ioloop=None,
               restrict_acs_hosts=None):
    self.ioloop = ioloop or tornado.ioloop.IOLoop.instance()
    self.restrict_acs_hosts = restrict_acs_hosts
    self.acs_url = acs_url
    self.port = port
    self.ping_path = ping_path
    self.get_parameter_key = get_parameter_key
    self.start_periodic_session = start_periodic_session
    self.my_ip = None
    self._periodic_callback = None
    self._start_periodic_timeout = None
    self.config_copy = None
    self._acs_config = acs_config
    self.config = ServerParameters()
    self.ConfigurePeriodicInform()

  def StartTransaction(self):
    if self.config_copy is None:
      self.config_copy = copy.deepcopy(self.config)

  def CommitTransaction(self):
    self.config_copy = None

  def AbandonTransaction(self):
    self.config = self.config_copy
    self.config_copy = None
    self.ConfigurePeriodicInform()

  def ValidateAcsUrl(self, value):
    """Checks if the URL passed is acceptable.  If not raises an exception."""
    if not self.restrict_acs_hosts or not value:
      return

    # Require https for the url scheme.
    split_url = urlparse.urlsplit(value)
    if split_url.scheme != 'https':
      raise ValueError('The ACS Host must be https: %r' % (value,))

    # Iterate over the restrict domain name list and see if one of
    # the restricted domain names matches the supplied url host name.
    restrict_hosts = re.split(r'[\s,]+', self.restrict_acs_hosts)
    for host in restrict_hosts:
      # Check the full hostname.
      if split_url.hostname == host:
        return

      # Check against the restrict host of form '.foo.com'
      if not host.startswith('.'):
        dotted_host = '.' + host
      else:
        dotted_host = host
      if split_url.hostname.endswith(dotted_host):
        return

    # If we don't find a valid host, raise an exception.
    raise ValueError('The ACS Host is not permissible: %r' % (value,))

  @property
  def CWMPRetryMinimumWaitInterval(self):
    return self.config.CWMPRetryMinimumWaitInterval

  @CWMPRetryMinimumWaitInterval.setter
  def CWMPRetryMinimumWaitInterval(self, value):
    self.config.CWMPRetryMinimumWaitInterval = int(value)

  @property
  def CWMPRetryIntervalMultiplier(self):
    return self.config.CWMPRetryIntervalMultiplier

  @CWMPRetryIntervalMultiplier.setter
  def CWMPRetryIntervalMultiplier(self, value):
    self.config.CWMPRetryIntervalMultiplier = int(value)

  @property
  def ConnectionRequestPassword(self):
    return self.config.ConnectionRequestPassword

  @ConnectionRequestPassword.setter
  def ConnectionRequestPassword(self, value):
    self.config.ConnectionRequestPassword = value

  @property
  def ConnectionRequestUsername(self):
    return self.config.ConnectionRequestUsername

  @ConnectionRequestUsername.setter
  def ConnectionRequestUsername(self, value):
    self.config.ConnectionRequestUsername = value

  @property
  def DefaultActiveNotificationThrottle(self):
    return self.config.DefaultActiveNotificationThrottle

  @DefaultActiveNotificationThrottle.setter
  def DefaultActiveNotificationThrottle(self, value):
    self.config.DefaultActiveNotificationThrottle = int(value)

  @property
  def EnableCWMP(self):
    return True

  @property
  def Password(self):
    return self.config.Password

  @Password.setter
  def Password(self, value):
    self.config.Password = value

  @property
  def Username(self):
    return self.config.Username

  @Username.setter
  def Username(self, value):
    self.config.Username = value

  def GetURL(self):
    """Return the ACS URL to use."""
    if self.acs_url:
      try:
        self.ValidateAcsUrl(self.acs_url)
        return self.acs_url
      except ValueError as e:
        print 'Supplied acs_url %r is invalid (%s)' % (self.acs_url, e)

    url = self._acs_config.GetAcsUrl()
    max_attempts = 20
    while url and max_attempts:
      try:
        self.ValidateAcsUrl(url)
        return url
      except ValueError as e:
        print 'Invalidating url %r (%s)' % (url, e)
        if not self._acs_config.InvalidateAcsUrl(url):
          print ('set-acs failed to invalidate url!'
                 'Something is extremely broken.')
          sys.exit(100)
        url = None
      url = self._acs_config.GetAcsUrl()
      max_attempts -= 1
    # If we get here, there is no valid platform url.
    return None

  def SetURL(self, value):
    self.ValidateAcsUrl(value)
    if self.acs_url:
      self.acs_url = value
    else:
      self._acs_config.SetAcsUrl(value)

  URL = property(GetURL, SetURL, None, 'tr-98/181 ManagementServer.URL')

  def _isIp6Address(self, ip):
    # pylint: disable-msg=W0702
    try:
      socket.inet_pton(socket.AF_INET6, ip)
    except:
      return False
    return True

  def _formatIP(self, ip):
    if self._isIp6Address(ip):
      return '[' + ip + ']'
    else:
      return ip

  def GetConnectionRequestURL(self):
    if self.my_ip and self.port and self.ping_path:
      path = self.ping_path if self.ping_path[0] != '/' else self.ping_path[1:]
      ip = self._formatIP(self.my_ip)
      return 'http://{0}:{1!s}/{2}'.format(ip, self.port, path)
    else:
      return ''
  ConnectionRequestURL = property(
      GetConnectionRequestURL, None, None,
      'tr-98/181 ManagementServer.ConnectionRequestURL')

  def GetParameterKey(self):
    if self.get_parameter_key is not None:
      return self.get_parameter_key()
    else:
      return ''
  ParameterKey = property(GetParameterKey, None, None,
                          'tr-98/181 ManagementServer.ParameterKey')

  def GetPeriodicInformEnable(self):
    return self.config.PeriodicInformEnable

  def SetPeriodicInformEnable(self, value):
    self.config.PeriodicInformEnable = cwmpbool.parse(value)
    self.ConfigurePeriodicInform()

  PeriodicInformEnable = property(
      GetPeriodicInformEnable, SetPeriodicInformEnable, None,
      'tr-98/181 ManagementServer.PeriodicInformEnable')

  def GetPeriodicInformInterval(self):
    return self.config.PeriodicInformInterval

  def SetPeriodicInformInterval(self, value):
    self.config.PeriodicInformInterval = int(value)
    self.ConfigurePeriodicInform()

  PeriodicInformInterval = property(
      GetPeriodicInformInterval, SetPeriodicInformInterval, None,
      'tr-98/181 ManagementServer.PeriodicInformInterval')

  def GetPeriodicInformTime(self):
    return self.config.PeriodicInformTime

  def SetPeriodicInformTime(self, value):
    self.config.PeriodicInformTime = value
    self.ConfigurePeriodicInform()

  PeriodicInformTime = property(
      GetPeriodicInformTime, SetPeriodicInformTime, None,
      'tr-98/181 ManagementServer.PeriodicInformTime')

  def ConfigurePeriodicInform(self):
    """Commit changes to PeriodicInform parameters."""
    if self._periodic_callback:
      self._periodic_callback.stop()
      self._periodic_callback = None
    if self._start_periodic_timeout:
      self.ioloop.remove_timeout(self._start_periodic_timeout)
      self._start_periodic_timeout = None

    # Delete the old periodic callback.
    if self._periodic_callback:
      self._periodic_callback.stop()
      self._periodic_callback = None

    if (self.config.PeriodicInformEnable and
        self.config.PeriodicInformInterval > 0):
      msec = self.config.PeriodicInformInterval * 1000
      self._periodic_callback = PERIODIC_CALLBACK(self.start_periodic_session,
                                                  msec, self.ioloop)
      if self.config.PeriodicInformTime:
        # PeriodicInformTime is just meant as an offset, not an actual time.
        # So if it's 25.5 hours in the future and the interval is 1 hour, then
        # the interesting part is the 0.5 hours, not the 25.
        #
        # timetuple might be in the past, but that's okay; the modulus
        # makes sure it's never negative.  (ie. (-3 % 5) == 2, in python)
        timetuple = cwmpdate.parse(self.config.PeriodicInformTime).timetuple()
        offset = ((time.mktime(timetuple) - time.time())
                  % float(self.config.PeriodicInformInterval))
      else:
        offset = 0.0
      self._start_periodic_timeout = self.ioloop.add_timeout(
          datetime.timedelta(seconds=offset), self.StartPeriodicInform)

  def StartPeriodicInform(self):
    self._periodic_callback.start()

  def SessionRetryWait(self, retry_count):
    """Calculate wait time before next session retry.

    See $SPEC3 section 3.2.1 for a description of the algorithm.

    Args:
      retry_count: integer number of retries attempted so far.

    Returns:
      Number of seconds to wait before initiating next session.
    """
    if retry_count == 0:
      return 0
    periodic_interval = self.config.PeriodicInformInterval
    if self.config.PeriodicInformInterval <= 0:
      periodic_interval = 30
    c = 10 if retry_count >= 10 else retry_count
    m = float(self.config.CWMPRetryMinimumWaitInterval)
    k = float(self.config.CWMPRetryIntervalMultiplier) / 1000.0
    start = m * math.pow(k, c-1)
    stop = start * k
    # pin start/stop to have a maximum value of PeriodicInformInterval
    start = int(min(start, periodic_interval/k))
    stop = int(min(stop, periodic_interval))
    randomwait = random.randrange(start, stop)
    return self.GetTimeout(SESSIONTIMEOUTFILE, randomwait)

  def GetTimeout(self, filename, default=60):
    """Get timeout value from file for testing."""
    try:
      return int(open(filename).readline().strip())
    except (IOError, ValueError):
      pass
    return default
