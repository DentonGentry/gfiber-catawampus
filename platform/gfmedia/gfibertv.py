#!/usr/bin/python
# Copyright 2012 Google Inc. All Rights Reserved.
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
"""Implement handling for the X_GOOGLE-COM_GFIBERTV vendor data model."""

__author__ = 'dgentry@google.com (Denton Gentry)'


import xmlrpclib
import google3
import tr.core
import tr.x_gfibertv_1_0
BASETV = tr.x_gfibertv_1_0.X_GOOGLE_COM_GFIBERTV_v1_0.X_GOOGLE_COM_GFIBERTV


class GFiberTvMailbox(BASETV.Mailbox):
  """Implementation of x-gfibertv.xml."""

  def __init__(self, url):
    super(GFiberTvMailbox, self).__init__()
    self.rpcclient = xmlrpclib.ServerProxy(url)
    self.Name = ''
    self.Node = ''

  def GetValue(self):
    try:
      return str(self.rpcclient.GetProperty(self.Name, self.Node))
    except xmlrpclib.Fault:
      raise IndexError('No such Property %s:%s' % (self.Node, self.Name))
    except (xmlrpclib.ProtocolError, IOError):
      raise IndexError(
          'Unable to access Property %s:%s' % (self.Node, self.Name))

  def SetValue(self, value):
    try:
      return str(self.rpcclient.SetProperty(self.Name, self.Node, value))
    except xmlrpclib.Fault:
      raise IndexError('No such Property %s:%s' % (self.Node, self.Name))
    except (xmlrpclib.ProtocolError, IOError):
      raise IndexError(
          'Unable to access Property %s:%s' % (self.Node, self.Name))

  Value = property(GetValue, SetValue, None,
                   'X_GOOGLE_COM_GFIBERTV_v1_0.Mailbox.Value')

  @property
  def NodeList(self):
    try:
      return str(', '.join(self.rpcclient.ListNodes()))
    except (xmlrpclib.Fault, xmlrpclib.ProtocolError, IOError):
      raise IndexError('Unable to list Nodes connected to this device.')

  @property
  def PropertyList(self):
    try:
      return str(', '.join(self.rpcclient.ListProperties(self.Node)))
    except (xmlrpclib.Fault, xmlrpclib.ProtocolError, IOError):
      raise IndexError('Unable to list Properties for node %s' % self.Node)
