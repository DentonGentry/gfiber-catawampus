#!/usr/bin/python
# Copyright 2011 Google Inc. All Rights Reserved.
#
# TR-069 has mandatory attribute names that don't comply with policy
#pylint: disable-msg=C6409
#pylint: disable-msg=W0404
#
"""Implement the inner handling for tr-98/181 ManagementServer."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import _fix_path  #pylint: disable-msg=W0611
import tr.x_gvsb_1_0

class Gvsb(tr.x_gvsb_1_0.X_GOOGLE_COM_GVSB_v1_0):
  GVSBSERVERFILE = "/tmp/gvsbserver"
  GVSBCHANNELFILE = "/tmp/gvsbchannel"

  def __init__(self):
    tr.x_gvsb_1_0.X_GOOGLE_COM_GVSB_v1_0.__init__(self)
    self._gvsbserver = None
    self._gvsb_channel_lineup = None
    self._written_gvsbserver = None
    self._written_gvsb_channel_lineup = None

  def GetGvsbServer(self):
    return self._gvsbserver

  def SetGvsbServer(self, value):
    self._gvsbserver = value
    self.ConfigureGvsb()

  def ValidateGvsbServer(self, value):
    return True

  GvsbServer = property(GetGvsbServer, SetGvsbServer, None,
                        'X_GVSB.GvsbServer')

  def GetGvsbChannelLineup(self):
    return self._gvsb_channel_lineup

  def SetGvsbChannelLineup(self, value):
    self._gvsb_channel_lineup = int(value)
    self.ConfigureGvsb()

  def ValidateGvsbChannelLineup(self, value):
    try:
      int(value)
    except:
      return False
    return True
  GvsbChannelLineup = property(GetGvsbChannelLineup, SetGvsbChannelLineup, None,
                               "X_GVSB.GvsbChannelLineup")

  def ConfigureGvsb(self):
    if self._gvsbserver != self._written_gvsbserver:
      f = open(self.GVSBSERVERFILE, "w")
      f.write(str(self._gvsbserver))
      f.close()
      self._written_gvsbserver = self._gvsbserver
    if self._gvsb_channel_lineup != self._written_gvsb_channel_lineup:
      f = open(self.GVSBCHANNELFILE, "w")
      f.write(str(self._gvsb_channel_lineup))
      f.close()
      self._written_gvsb_channel_lineup = self._gvsb_channel_lineup


def main():
  pass

if __name__ == '__main__':
  main()
