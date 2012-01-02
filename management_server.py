#!/usr/bin/python
#
# Copyright 2011 Google Inc. All Rights Reserved.
#
# TR-069 has mandatory attribute names that don't comply with policy
#pylint: disable-msg=C6409

"""Implementation of tr-181 Device.ManagementServer hierarchy of objects.

Handles the Device.ManagementServer portion of TR-181, as described
in http://www.broadband-forum.org/cwmp/tr-181-2-2-0.html
"""

__author__ = 'dgentry@google.com (Denton Gentry)'

import tr.core
import tr.tr181_v2_2

BASEMGMT = tr.tr181_v2_2.Device_v2_2.Device.ManagementServer

class ManagementServer(BASEMGMT):
  def __init__(self):
    BASEMGMT.__init__(self)

    self.Unexport('DownloadProgressURL')
    self.Unexport('KickURL')
    self.Unexport('STUNMaximumKeepAlivePeriod')
    self.Unexport('STUNMinimumKeepAlivePeriod')
    self.Unexport('STUNPassword')
    self.Unexport('STUNServerAddress')
    self.Unexport('STUNServerPort')
    self.Unexport('STUNUsername')
    self.Unexport('UDPConnectionRequestAddress')
    self.Unexport('NATDetected')

    self.CWMPRetryIntervalMultiplier = 1
    self.CWMPRetryMinimumWaitInterval = 1000
    self.ConnectionRequestPassword = ''
    self.ConnectionRequestURL = ''
    self.ConnectionRequestUsername = ''
    self.DefaultActiveNotificationThrottle = False
    self.EnableCWMP = True
    self.ManageableDeviceList = {}
    self.ParameterKey = ''
    self.Password = ''
    self.PeriodicInformEnable = False
    self.PeriodicInformInterval = 0
    self.PeriodicInformTime = 0
    self.STUNEnable = False
    self.URL = ''
    self.UpgradesManaged = True
    self.Username = ''

  @property
  def ManageableDeviceNumberOfEntries(self):
    return 0


def main():
  pass

if __name__ == '__main__':
  main()
