#!/usr/bin/python
#
# Copyright 2012 Google Inc. All Rights Reserved.
#
# TR-069 has mandatory attribute names that don't comply with policy
#pylint: disable-msg=C6409

"""Implementation of the x-catawampus-org vendor data model.
"""

__author__ = 'dgentry@google.com (Denton Gentry)'

import google3

import json
import sys
import tr.core
import tr.x_catawampus_1_0

BASEDM = tr.x_catawampus_1_0.X_CATAWAMPUS_ORG_CATAWAMPUS_v1_0


#pylint: disable-msg=W0231
class CatawampusDm(BASEDM):
  """Implementation of x-catawampus-1.0. See tr/schema/x-catawampus.xml"""

  def __init__(self):
    BASEDM.__init__(self)

  @property
  def RuntimeEnvInfo(self):
    python = dict()
    python["exec_prefix"] = sys.exec_prefix
    python["executable"] = sys.executable
    python["path"] = str(sys.path)
    python["platform"] = sys.platform
    python["prefix"] = sys.prefix
    python["version"] = sys.version

    env = dict()
    env["python"] = python

    return json.dumps(env)


if __name__ == '__main__':
  sys.path.append("../")
  cm = CatawampusDm()
  print tr.core.Dump(cm)
