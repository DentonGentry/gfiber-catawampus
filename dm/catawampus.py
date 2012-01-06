#!/usr/bin/python
#
# Copyright 2012 Google Inc. All Rights Reserved.
#
# TR-069 has mandatory attribute names that don't comply with policy
#pylint: disable-msg=C6409

"""Implementation of x-catawampus object.

"""

__author__ = 'dgentry@google.com (Denton Gentry)'

import sys
import tr.core
import tr.x_catawampus_1_0

BASEDM = tr.x_catawampus_1_0.X_CATAWAMPUS_ORG_CATAWAMPUS_v1_0


#pylint: disable-msg=W0231
class CatawampusDm(BASEDM):
  """Implementation of x-catawampus-1.0. See tr/schema/x-catawampus.xml"""

  def __init__(self):
    BASEDM.__init__(self)
    self.RuntimeEnvInfo = "Boo!"


def main():
  sys.path.append("../")
  cm = CatawampusDm()
  print tr.core.Dump(cm)

if __name__ == '__main__':
  main()
