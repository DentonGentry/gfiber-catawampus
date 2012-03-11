#!/usr/bin/python
#
# Copyright 2012 Google Inc. All Rights Reserved.
#
# TR-069 has mandatory attribute names that don't comply with policy
#pylint: disable-msg=C6409

"""Implementation of tr-181 MoCA objects for Broadcom chipsets."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import re
import subprocess
import pynetlinux
import tr.core
import tr.tr181_v2_2
import netdev


BASE181MOCA = tr.tr181_v2_2.Device_v2_2.Device.MoCA
MOCACTL = '/bin/mocactl'
PYNETIFCONF = pynetlinux.ifconfig.Interface


class BrcmMocaInterface(BASE181MOCA.Interface):
  """An implementation of tr181 Device.MoCA.Interface for Broadcom chipsets."""

  def __init__(self, ifname, upstream=False):
    BASE181MOCA.Interface.__init__(self)
    self.ifname = ifname
    self.upstream = upstream
    self._pynet = PYNETIFCONF(ifname)

    self.Unexport('Alias')
    self.Unexport('KeyPassphrase')
    self.AssociatedDeviceList = tr.core.AutoDict(
        'AssociatedDeviceList', iteritems=self.IterAssociatedDevices,
        getitem=self.GetAssociatedDeviceByIndex)

  def IntOrZero(self, val):
    try:
      return int(val)
    except (ValueError, TypeError):
      return 0

  # TODO(dgentry) need @sessioncache decorator
  def _MocaCtlShowStatus(self):
    """Return output of mocactl show --status."""
    mc = subprocess.Popen([MOCACTL, 'show', '--status'], stdout=subprocess.PIPE)
    out, _ = mc.communicate(None)
    return out.splitlines()

  def _MocaCtlGetField(self, outfcn, field):
    """Look for one field in a mocactl command.

    ex: field='SwVersion' would return 5.6.789 from
    vendorId              : 999999999   HwVersion             : 0x12345678
    SwVersion             : 5.6.789     self MoCA Version     : 0x11

    Args:
      outfcn: a function to call, which must return a list of text lines.
      field: the text string to look for.
    Returns:
      The value of the field, or None.
    """

    m_re = re.compile(field + '\s*:\s+(\S+)')
    for line in outfcn():
      mr = m_re.search(line)
      if mr is not None:
        return mr.group(1)
    return None

  @property
  def Status(self):
    if not self._pynet.is_up():
      return 'Down'
    (speed, duplex, auto, link_up) = self._pynet.get_link_info()
    if link_up:
      return 'Up'
    else:
      return 'Dormant'

  @property
  def Name(self):
    return self.ifname

  @property
  def LowerLayers(self):
    # In theory this is writeable, but it is nonsensical to write to it.
    return ''

  @property
  def Upstream(self):
    return self.upstream

  @property
  def MACAddress(self):
    return self._pynet.get_mac()

  @property
  def FirmwareVersion(self):
    ver = self._MocaCtlGetField(self._MocaCtlShowStatus, 'SwVersion')
    return ver if ver else '0'

  @property
  def NetworkCoordinator(self):
    nodeid = self._MocaCtlGetField(self._MocaCtlShowStatus, 'ncNodeId')
    return self.IntOrZero(nodeid)

  @property
  def NodeID(self):
    nodeid = self._MocaCtlGetField(self._MocaCtlShowStatus, 'nodeId')
    return self.IntOrZero(nodeid)

  @property
  def AssociatedDeviceNumberOfEntries(self):
    return len(self.AssociatedDeviceList)

  @property
  def LastChange(self):
    up = self._MocaCtlGetField(self._MocaCtlShowStatus, 'linkUpTime').split(':')
    secs = 0
    for t in up:
      # linkUpTime ex: '23h:41m:30s'
      num = self.IntOrZero(t[:-1])
      if t[-1] == 'y':
        secs += int(num * (365.25 * 24.0 * 60.0 * 60.0))
      elif t[-1] == 'w':
        secs += num * (7 * 24 * 60 * 60)
      elif t[-1] == 'd':
        secs += num * (24 * 60 * 60)
      elif t[-1] == 'h':
        secs += num * (60 * 60)
      elif t[-1] == 'm':
        secs += num * 60
      elif t[-1] == 's':
        secs += num
    return secs

  def _MocaCtlGetNodeIDs(self):
    """Return a list of active MoCA Node IDs."""
    mc = subprocess.Popen([MOCACTL, 'showtbl', '--nodestats'],
                          stdout=subprocess.PIPE)
    out, _ = mc.communicate(None)
    node_re = re.compile('\ANode\s*: (\d+)')
    nodes = set()
    for line in out.splitlines():
      node = node_re.search(line)
      if node is not None:
        nodes.add(int(node.group(1)))
    return list(nodes)

  def GetAssociatedDevice(self, nodeid):
    """Get an AssociatedDevice object for the given NodeID."""
    ad = BrcmMocaAssociatedDevice(nodeid)
    if ad:
      ad.ValidateExports()
    return ad

  def IterAssociatedDevices(self):
    """Retrieves a list of all associated devices."""
    mocanodes = self._MocaCtlGetNodeIDs()
    for idx, nodeid in enumerate(mocanodes):
      yield idx, self.GetAssociatedDevice(nodeid)

  def GetAssociatedDeviceByIndex(self, index):
    mocanodes = self._MocaCtlGetNodeIDs()
    return self.GetAssociatedDevice(mocanodes[index])


class BrcmMocaInterfaceStatsLinux26(netdev.NetdevStatsLinux26,
                                    BASE181MOCA.Interface.Stats):
  """tr181 Device.MoCA.Interface.Stats for Broadcom chipsets."""

  def __init__(self, ifname):
    netdev.NetdevStatsLinux26.__init__(self, ifname)
    BASE181MOCA.Interface.Stats.__init__(self)


class BrcmMocaAssociatedDevice(BASE181MOCA.Interface.AssociatedDevice):
  """tr-181 Device.MoCA.Interface.AssociatedDevice for Broadcom chipsets."""

  def __init__(self, nodeid):
    BASE181MOCA.Interface.AssociatedDevice.__init__(self)
    self.NodeID = nodeid
    self.MACAddress = ''
    self.PreferredNC = False
    self.Unexport('HighestVersion')
    self.PHYTxRate = 0
    self.PHYRxRate = 0
    self.TxPowerControlReduction = 0
    self.RxPowerLevel = 0
    self.TxBcastRate = 0
    self.RxBcastPowerLevel = 0
    self.TxPackets = 0
    self.RxPackets = 0
    self.RxErroredAndMissedPackets = 0
    self.QAM256Capable = 0
    self.PacketAggregationCapability = 0
    self.RxSNR = 0
    self.Unexport('Active')

    self.ParseNodeStatus()
    self.ParseNodeStats()

  def IntOrZero(self, arg):
    try:
      return int(arg)
    except ValueError:
      return 0

  def FloatOrZero(self, arg):
    try:
      return float(arg)
    except ValueError:
      return 0.0

  def ParseNodeStatus(self):
    """Run mocactl show --nodestatus for this node, parse the output."""
    mac_re = re.compile(
        '^MAC Address\s+: ((?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2})')
    pnc_re = re.compile('Preferred NC\s+: (\d+)')
    ptx_re = re.compile('\ATxUc.+?(\d+[.]?\d*)\s+dBm.*?(\d+)\s+bps')
    prx_re = re.compile('\ARxUc.+?(\d+[.]?\d*)\s+dBm.*?(\d+)\s+bps'
                        '\s+(\d+[.]?\d*) dB')
    rxb_re = re.compile('\ARxBc.+?(\d+[.]?\d*)\s+dBm.*?(\d+)\s+bps')
    qam_re = re.compile('256 QAM capable\s+:\s+(\d+)')
    agg_re = re.compile('Aggregated PDUs\s+:\s+(\d+)')
    mc = subprocess.Popen([MOCACTL, 'show', '--nodestatus', str(self.NodeID)],
                          stdout=subprocess.PIPE)
    out, _ = mc.communicate(None)
    for line in out.splitlines():
      mac = mac_re.search(line)
      if mac is not None:
        self.MACAddress = mac.group(1)
      pnc = pnc_re.search(line)
      if pnc is not None:
        self.PreferredNC = False if pnc.group(1) is '0' else True
      ptx = ptx_re.search(line)
      if ptx is not None:
        self.PHYTxRate = self.IntOrZero(ptx.group(2)) / 1000000
        self.TxPowerControlReduction = int(self.FloatOrZero(ptx.group(1)))
      prx = prx_re.search(line)
      if prx is not None:
        self.PHYRxRate = self.IntOrZero(prx.group(2)) / 1000000
        self.RxPowerLevel = int(self.FloatOrZero(prx.group(1)))
        # TODO(dgentry) This cannot be right. SNR should be dB, not an integer.
        self.RxSNR = int(self.FloatOrZero(prx.group(3)))
      rxb = rxb_re.search(line)
      if rxb is not None:
        self.TxBcastRate = self.IntOrZero(rxb.group(2)) / 1000000
        self.RxBcastPowerLevel = int(self.FloatOrZero(rxb.group(1)))
      qam = qam_re.search(line)
      if qam is not None:
        self.QAM256Capable = False if qam.group(1) is '0' else True
      agg = agg_re.search(line)
      if agg is not None:
        self.PacketAggregationCapability = self.IntOrZero(agg.group(1))

  def ParseNodeStats(self):
    """Run mocactl show --nodestats for this node, parse the output."""
    tx_re = re.compile('Unicast Tx Pkts To Node\s+: (\d+)')
    rx_re = re.compile('Unicast Rx Pkts From Node\s+: (\d+)')
    e1_re = re.compile('Rx CodeWord ErrorAndUnCorrected\s+: (\d+)')
    e2_re = re.compile('Rx NoSync Errors\s+: (\d+)')
    mc = subprocess.Popen([MOCACTL, 'show', '--nodestats', str(self.NodeID)],
                          stdout=subprocess.PIPE)
    out, _ = mc.communicate(None)
    rx_err = 0
    for line in out.splitlines():
      tx = tx_re.search(line)
      if tx is not None:
        self.TxPackets = self.IntOrZero(tx.group(1))
      rx = rx_re.search(line)
      if rx is not None:
        self.RxPackets = self.IntOrZero(rx.group(1))
      e1 = e1_re.search(line)
      if e1 is not None:
        rx_err += self.IntOrZero(e1.group(1))
      e2 = e2_re.search(line)
      if e2 is not None:
        rx_err += self.IntOrZero(e2.group(1))
    self.RxErroredAndMissedPackets = rx_err


class BrcmMoca(BASE181MOCA):
  """An implementation of tr181 Device.MoCA for Broadcom chipsets."""

  def __init__(self):
    BASE181MOCA.__init__(self)
    self.InterfaceList = {}

  @property
  def InterfaceNumberOfEntries(self):
    return len(self.InterfaceList)


def main():
  pass

if __name__ == '__main__':
  main()
