#!/usr/bin/python
#
# Copyright 2012 Google Inc. All Rights Reserved.
#
# TR-069 has mandatory attribute names that don't comply with policy
#pylint: disable-msg=C6409

"""Implementation of tr-981 WLAN objects for Broadcom Wifi chipsets. """

__author__ = 'dgentry@google.com (Denton Gentry)'

import re
import subprocess
import tr.core
import tr.tr098_v1_2

BASEWIFI = tr.tr098_v1_2.InternetGatewayDevice_v1_4.InternetGatewayDevice.LANDevice.WLANConfiguration
WL_EXE = "/usr/bin/wl"

class BrcmWifiWlanConfiguration(BASEWIFI):
  def __init__(self):
    BASEWIFI.__init__(self)
    self.AutoChannelEnable = tr.core.TODO()
    self.BasicAuthenticationMode = tr.core.TODO()
    self.BasicEncryptionModes = tr.core.TODO()
    self.BeaconType = tr.core.TODO()
    self.DeviceOperationMode = tr.core.TODO()
    self.IEEE11iAuthenticationMode = tr.core.TODO()
    self.IEEE11iEncryptionModes = tr.core.TODO()
    self.Name = tr.core.TODO()
    self.SSIDAdvertisementEnabled = tr.core.TODO()
    self.Standard = tr.core.TODO()
    self.TotalAssociations = 0
    self.TransmitPower = tr.core.TODO()
    self.TransmitPowerSupported = tr.core.TODO()
    self.UAPSDEnable = tr.core.TODO()
    self.UAPSDSupported = tr.core.TODO()
    self.WMMEnable = tr.core.TODO()
    self.WMMSupported = tr.core.TODO()
    self.WPAAuthenticationMode = tr.core.TODO()
    self.WPAEncryptionModes = tr.core.TODO()
    #objects=['Stats',
    #         'WPS'],
    #lists=['APWMMParameter',
    #       'AssociatedDevice',
    #       'PreSharedKey',
    #       'STAWMMParameter'])

  # TODO(dgentry) need a @sessioncache decorator
  def _GetWlCounters(self):
    wl = subprocess.Popen([WL_EXE, "counters"], stdout=subprocess.PIPE)
    out, err = wl.communicate(None)

    # match three different types of stat output:
    # rxuflo: 1 2 3 4 5 6
    # rxfilter 1
    # d11_txretrie
    st = re.compile("(\w+:?(?: \d+)*)")

    stats = st.findall(out)
    r1 = re.compile("(\w+): (.+)")
    r2 = re.compile("(\w+) (\d+)")
    r3 = re.compile("(\w+)")
    sdict = dict()
    for stat in stats:
      p1 = r1.match(stat)
      p2 = r2.match(stat)
      p3 = r3.match(stat)
      if p1 is not None:
        sdict[p1.group(1).lower()] = p1.group(2).split()
      elif p2 is not None:
        sdict[p2.group(1).lower()] = p2.group(2)
      elif p3 is not None:
        sdict[p3.group(1).lower()] = "0"
    return sdict

  @property  # TODO(dgentry) need @sessioncache decorator
  def Channel(self):
    wl = subprocess.Popen([WL_EXE, "channel"], stdout=subprocess.PIPE)
    out, err = wl.communicate(None)
    chan_re = re.compile("current mac channel(?:\s+)(\d+)")
    for line in out.splitlines():
      mr = chan_re.match(line)
      if mr is not None:
        return int(mr.group(1))
    return 0

  def _OutputContiguousRanges(self, seq):
    """Given an integer sequence, return contiguous ranges.

    Ex: [1,2,3,4,5] will return '1-5'
    """
    in_range = False
    prev = seq[0]
    output = list(str(seq[0]))
    for item in seq[1:]:
      if item == prev + 1:
        if not in_range:
          in_range = True
          output.append("-")
      else:
        if in_range:
          output.append(str(prev))
        output.append("," + str(item))
        in_range = False
      prev = item
    if in_range:
      output.append(str(prev))
    return ''.join(output)

  @property  # TODO(dgentry) need @sessioncache decorator
  def Channels(self):
    wl = subprocess.Popen([WL_EXE, "channels"], stdout=subprocess.PIPE)
    out, err = wl.communicate(None)
    channels = [int(x) for x in out.split()]
    return self._OutputContiguousRanges(channels)

  @property
  def SSID(self):
    wl = subprocess.Popen([WL_EXE, "ssid"], stdout=subprocess.PIPE)
    out, err = wl.communicate(None)
    ssid_re = re.compile('Current SSID: "(.*)"')
    for line in out.splitlines():
      ssid = ssid_re.match(line)
      if ssid is not None:
        return ssid.group(1)
    return ""

  @property
  def TotalBytesReceived(self):
    counters = self._GetWlCounters()
    return int(counters.get('rxbyte', 0))

  @property
  def TotalBytesSent(self):
    counters = self._GetWlCounters()
    return int(counters.get('txbyte', 0))

  @property
  def TotalPacketsReceived(self):
    counters = self._GetWlCounters()
    return int(counters.get('rxframe', 0))

  @property
  def TotalPacketsSent(self):
    counters = self._GetWlCounters()
    return int(counters.get('txframe', 0))





def main():
  pass

if __name__ == '__main__':
  main()
