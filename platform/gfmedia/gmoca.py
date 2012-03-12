#!/usr/bin/python
# Copyright 2012 Google Inc. All Rights Reserved.
#
# TR-069 has mandatory attribute names that don't comply with policy
#pylint: disable-msg=C6409
#pylint: disable-msg=W0404
#
"""Implement handling for the X_GOOGLE-COM_GMOCA vendor data model."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import base64
import bz2
import cStringIO
import subprocess
import google3
import tr.x_gmoca_1_0


# Unit tests can override these.
MOCACTL = '/bin/mocactl'


class GMoCA(tr.x_gmoca_1_0.X_GOOGLE_COM_GMOCA_v1_0):
  """Implementation of x-gmoca.xml."""

  MOCACMDS = [['show', '--status'],
              ['show', '--config'],
              ['show', '--initparms'],
              ['show', '--stats'],
              ['showtbl', '--nodestatus'],
              ['showtbl', '--nodestats'],
              ['showtbl', '--ucfwd'],
              ['showtbl', '--mcfwd'],
              ['showtbl', '--srcaddr']]

  def __init__(self):
    super(GMoCA, self).__init__()

  @property
  def DebugOutput(self):
    compr = bz2.BZ2Compressor()
    cdata = cStringIO.StringIO()
    for cmd in self.MOCACMDS:
      cdata.write(compr.compress('X_GOOGLE-COM_GMOCA --------------------\n'))
      cdata.write(compr.compress(' '.join(cmd) + '\n'))
      try:
        mc = subprocess.Popen([MOCACTL] + cmd, stdout=subprocess.PIPE)
        out, _ = mc.communicate(None)
        cdata.write(compr.compress(out))
      except IOError:
        continue
    cdata.write(compr.flush())
    return base64.b64encode(cdata.getvalue())


def main():
  pass

if __name__ == '__main__':
  main()
