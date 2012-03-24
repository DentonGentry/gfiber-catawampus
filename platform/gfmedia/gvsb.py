#!/usr/bin/python
# Copyright 2011 Google Inc. All Rights Reserved.
#
# TR-069 has mandatory attribute names that don't comply with policy
#pylint: disable-msg=C6409
#pylint: disable-msg=W0404
#
"""Implement the X_GOOGLE-COM_GVSB vendor data model."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import google3
import tr.x_gvsb_1_0

# Unit tests can override these.
GVSBSERVERFILE = '/tmp/gvsbhost'
GVSBCHANNELFILE = '/tmp/gvsbchannel'
GVSBKICKFILE = '/tmp/gvsbkick'


class Gvsb(tr.x_gvsb_1_0.X_GOOGLE_COM_GVSB_v1_1):
  """Implementation of x-gvsb.xml."""

  def __init__(self):
    super(Gvsb, self).__init__()
    self._gvsbserver = None
    self._gvsb_channel_lineup = None
    self._gvsb_kick = None
    self._written_gvsbserver = None
    self._written_gvsb_channel_lineup = None
    self._written_gvsb_kick = None
    self.WriteFile(GVSBSERVERFILE, '')
    self.WriteFile(GVSBCHANNELFILE, '')
    self.WriteFile(GVSBKICKFILE, '')

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
    # pylint: disable-msg=W0702
    try:
      int(value)
    except:
      return False
    return True

  GvsbChannelLineup = property(GetGvsbChannelLineup, SetGvsbChannelLineup, None,
                               'X_GVSB.GvsbChannelLineup')

  def GetGvsbKick(self):
    return self._gvsb_kick

  def SetGvsbKick(self, value):
    self._gvsb_kick = value
    self.ConfigureGvsb()

  def ValidateGvsbKick(self, value):
    return True

  GvsbKick = property(GetGvsbKick, SetGvsbKick, None, 'X_GVSB.GvsbKick')

  def WriteFile(self, filename, content):
    try:
      f = open(filename, 'w')
      f.write(content)
      f.close()
      return True
    except IOError:
      return False

  def ConfigureGvsb(self):
    if self._gvsbserver != self._written_gvsbserver:
      if self.WriteFile(GVSBSERVERFILE, str(self._gvsbserver)):
        self._written_gvsbserver = self._gvsbserver
    if self._gvsb_channel_lineup != self._written_gvsb_channel_lineup:
      if self.WriteFile(GVSBCHANNELFILE, str(self._gvsb_channel_lineup)):
        self._written_gvsb_channel_lineup = self._gvsb_channel_lineup
    if self._gvsb_kick != self._written_gvsb_kick:
      if self.WriteFile(GVSBKICKFILE, self._gvsb_kick):
        self._written_gvsb_kick = self._gvsb_kick


def main():
  pass

if __name__ == '__main__':
  main()
