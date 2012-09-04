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

import copy
import os
import xmlrpclib
import google3
import tr.core
import tr.x_gfibertv_1_0
BASETV = tr.x_gfibertv_1_0.X_GOOGLE_COM_GFIBERTV_v1_0.X_GOOGLE_COM_GFIBERTV

NICKFILE = '/tmp/nicknames'
NICKFILE_TMP = '/tmp/nicknames.tmp'


class GFiberTvConfig(object):
  """Class to store configuration settings for GFiberTV."""
  pass


class PropertiesConfig(object):
  """Class to store configuration settings for DeviceProperties."""
  pass


class GFiberTv(BASETV):
  """Implementation of x-gfibertv.xml."""

  def __init__(self, mailbox_url):
    super(GFiberTv, self).__init__()
    self.Mailbox = GFiberTvMailbox(mailbox_url)
    self.config = GFiberTvConfig()
    self.config.nicknames = dict()
    self.config_old = None
    self.DevicePropertiesList = tr.core.AutoDict(
        'X_GOOGLE_COM_GFIBERTV.DevicePropertiesList',
        iteritems=self.IterProperties, getitem=self.GetProperties,
        setitem=self.SetProperties, delitem=self.DelProperties)

  class DeviceProperties(BASETV.DeviceProperties):
    """Implementation of gfibertv.DeviceProperties."""

    def __init__(self):
      super(GFiberTv.DeviceProperties, self).__init__()
      self.config = PropertiesConfig()
      # nick_name is a unicode string.
      self.config.nick_name = ''
      self.config.serial_number = ''

    def StartTransaction(self):
      # NOTE(jnewlin): If an inner object is added, we need to do deepcopy.
      self.config_old = copy.copy(self.config)

    def AbandonTransaction(self):
      self.config = self.config_old
      self.config_old = None

    def CommitTransaction(self):
      self.config_old = None

    @property
    def NickName(self):
      return self.config.nick_name.decode('utf-8')

    @NickName.setter
    def NickName(self, value):
      # TODO(jnewlin): Need some sanity here so the user can't enter
      # a value that hoses the file, like a '/' or newline.
      tmp_uni = unicode(value, 'utf-8')
      tmp_uni = tmp_uni.replace(u'\n', u'')
      tmp_uni = tmp_uni.replace(u'\r', u'')
      self.config.nick_name = tmp_uni

    @property
    def SerialNumber(self):
      return self.config.serial_number

    @SerialNumber.setter
    def SerialNumber(self, value):
      self.config.serial_number = value

  def StartTransaction(self):
    assert self.config_old is None
    self.config_old = copy.copy(self.config)

  def AbandonTransaction(self):
    self.config = self.config_old
    self.config_old = None

  def CommitTransaction(self):
    """Write out the config file for Sage."""
    with file(NICKFILE_TMP, 'w') as f:
      if self.config.nicknames:
        serials = []
        for nn in self.config.nicknames.itervalues():
          f.write('%s/nickname=%s\n' % (
              nn.SerialNumber, nn.config.nick_name.encode('unicode-escape')))
          serials.append(nn.SerialNumber)
        f.write('SERIALS=%s\n' % ','.join(serials))
    os.rename(NICKFILE_TMP, NICKFILE)
    self.config_old = None

  @property
  def DevicePropertiesNumberOfEntries(self):
    return len(self.config.nicknames)

  def IterProperties(self):
    return self.config.nicknames.iteritems()

  def GetProperties(self, key):
    return self.config.nicknames[key]

  def SetProperties(self, key, value):
    self.config.nicknames[key] = value

  def DelProperties(self, key):
    del self.config.nicknames[key]


class GFiberTvMailbox(BASETV.Mailbox):
  """Implementation of x-gfibertv.xml."""

  def __init__(self, url):
    super(GFiberTvMailbox, self).__init__()
    self.rpcclient = xmlrpclib.ServerProxy(url)
    self.Name = ''
    self.Node = ''

  def GetValue(self):
    if not self.Name:
      return None
    try:
      return str(self.rpcclient.GetProperty(self.Name, self.Node))
    except xmlrpclib.Fault:
      raise IndexError('No such Property %s:%s' % (self.Node, self.Name))
    except (xmlrpclib.ProtocolError, IOError):
      raise IndexError(
          'Unable to access Property %s:%s' % (self.Node, self.Name))

  def SetValue(self, value):
    try:
      return str(self.rpcclient.SetProperty(self.Name, value, self.Node))
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
    except (xmlrpclib.Fault, xmlrpclib.ProtocolError, IOError), e:
      print 'gfibertv.NodeList: %s' % e
      return {}
