#!/usr/bin/python
# Copyright 2011 Google Inc. All Rights Reserved.
#
# TR-069 has mandatory attribute names that don't comply with policy
#pylint: disable-msg=C6409
#pylint: disable-msg=W0404
#
"""Implement the inner handling for tr-98/181 ManagementServer."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import math
import random
import socket
import time

import google3
import tornado.ioloop
import cwmpbool
import cwmpdate


# Allow unit tests to override with a mock
PERIODIC_CALLBACK = tornado.ioloop.PeriodicCallback


class CpeManagementServer(object):
  """Inner class implementing tr-98 & 181 ManagementServer."""

  def __init__(self, acs_url_file, port, ping_path, get_parameter_key=None,
               start_periodic_session=None, ioloop=None):
    self.ioloop = ioloop or tornado.ioloop.IOLoop.instance()
    self.acs_url_file = acs_url_file
    self.port = port
    self.ping_path = ping_path
    self.get_parameter_key = get_parameter_key
    self.start_periodic_session = start_periodic_session
    self.my_ip = None
    self._periodic_callback = None
    self._start_periodic_timeout = None

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
    self.Password = ''
    self._PeriodicInformEnable = False
    self._PeriodicInformInterval = 0
    self._PeriodicInformTime = 0
    self.Username = ''

  # TODO(dgentry) - monitor acs_url_file for changes. $SPEC3 3.2.1 requires
  # an immediate Inform when the ACS URL changes.

  def GetURL(self):
    try:
      f = open(self.acs_url_file, 'r')
      line = f.readline().strip()
      f.close()
    except IOError:
      line = ''
    return line
  URL = property(GetURL, None, None, 'tr-98/181 ManagementServer.URL')

  def isIp6Address(self, ip):
    # pylint: disable-msg=W0702
    try:
      socket.inet_pton(socket.AF_INET6, ip)
    except:
      return False
    return True

  def formatIP(self, ip):
    if self.isIp6Address(ip):
      return '[' + ip + ']'
    else:
      return ip

  def GetConnectionRequestURL(self):
    if self.my_ip and self.port and self.ping_path:
      path = self.ping_path if self.ping_path[0] != '/' else self.ping_path[1:]
      ip = self.formatIP(self.my_ip)
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
    return self._PeriodicInformEnable

  def SetPeriodicInformEnable(self, value):
    self._PeriodicInformEnable = cwmpbool.parse(value)
    self.ConfigurePeriodicInform()

  def ValidatePeriodicInformEnable(self, value):
    return cwmpbool.valid(value)

  PeriodicInformEnable = property(
      GetPeriodicInformEnable, SetPeriodicInformEnable, None,
      'tr-98/181 ManagementServer.PeriodicInformEnable')

  def GetPeriodicInformInterval(self):
    return self._PeriodicInformInterval

  def SetPeriodicInformInterval(self, value):
    self._PeriodicInformInterval = int(value)
    self.ConfigurePeriodicInform()

  def ValidatePeriodicInformInterval(self, value):
    v = int(value)
    return True if v >= 1 else False

  PeriodicInformInterval = property(
      GetPeriodicInformInterval, SetPeriodicInformInterval, None,
      'tr-98/181 ManagementServer.PeriodicInformInterval')

  def GetPeriodicInformTime(self):
    return self._PeriodicInformTime

  def SetPeriodicInformTime(self, value):
    self._PeriodicInformTime = value
    self.ConfigurePeriodicInform()

  def ValidatePeriodicInformTime(self, value):
    return cwmpdate.valid(value)

  PeriodicInformTime = property(
      GetPeriodicInformTime, SetPeriodicInformTime, None,
      'tr-98/181 ManagementServer.PeriodicInformTime')

  def ConfigurePeriodicInform(self):
    if self._periodic_callback:
      self._periodic_callback.stop()
      self._periodic_callback = None
    if self._start_periodic_timeout:
      self.ioloop.remove_timeout(self._start_periodic_timeout)
      self._start_periodic_timeout = None

    if self._PeriodicInformEnable and self._PeriodicInformInterval > 0:
      msec = self._PeriodicInformInterval * 1000
      self._periodic_callback = PERIODIC_CALLBACK(self.DoPeriodicInform,
                                                  msec, self.ioloop)
      if self._PeriodicInformTime:
        timetuple = cwmpdate.parse(self._PeriodicInformTime).timetuple()
        wait = time.mktime(timetuple) - time.time()
        if wait < 0.0:  # PeriodicInformTime has already passed
          wait %= float(self._PeriodicInformInterval)
          wait = float(self._PeriodicInformInterval) + wait
      else:
        wait = 0.0
      self._start_periodic_timeout = self.ioloop.add_timeout(
          wait, self.StartPeriodicInform)

  def StartPeriodicInform(self):
    self._periodic_callback.start()

  def DoPeriodicInform(self):
    self.start_periodic_session()

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
    c = 10 if retry_count >= 10 else retry_count
    m = float(self.CWMPRetryMinimumWaitInterval)
    k = float(self.CWMPRetryIntervalMultiplier) / 1000.0
    start = math.floor(m * math.pow(k, c-1))
    stop = math.floor(m * math.pow(k, c))
    return random.randrange(start, stop)


def main():
  pass

if __name__ == '__main__':
  main()
