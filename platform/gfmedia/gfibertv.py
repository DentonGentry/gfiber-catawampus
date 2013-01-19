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
# pylint: disable-msg=C6409
# pylint: disable-msg=W0404
#
"""Implement handling for the X_GOOGLE-COM_GFIBERTV vendor data model."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import copy
import errno
import os
import xmlrpclib
import google3
import tr.core
import tr.cwmpbool
import tr.cwmpdate
import tr.helpers
import tr.x_gfibertv_1_0
BASETV = tr.x_gfibertv_1_0.X_GOOGLE_COM_GFIBERTV_v1_0.X_GOOGLE_COM_GFIBERTV

NICKFILE = '/tmp/nicknames'
NICKFILE_TMP = '/tmp/nicknames.tmp'
BTDEVICES = '/user/bsa/bt_devices.xml'
BTHHDEVICES = '/user/bsa/bt_hh_devices.xml'
BTCONFIG = '/user/bsa/bt_config.xml'
BTNOPAIRING = '/usr/bsa/nopairing'
EASADDRFILE = '/tmp/eas_service_address'
EASFIPSFILE = '/tmp/eas_fips'
EASHEARTBEATFILE = '/tmp/eas_heartbeat'
EASPORTFILE = '/tmp/eas_service_port'


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
    self.config.bt_devices = None
    self.config.bt_hh_devices = None
    self.config.bt_config = None
    self.config.bt_nopairing = None
    self.config.eas_code = None
    self.config.eas_service_addr = None
    self.config.eas_service_port = None
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
      self.parent = None

    def StartTransaction(self):
      # NOTE(jnewlin): If an inner object is added, we need to do deepcopy.
      self.config_old = copy.copy(self.config)

    def AbandonTransaction(self):
      self.config = self.config_old
      self.config_old = None

    def CommitTransaction(self):
      self.config_old = None
      self.parent.WriteNicknamesFile()

    @property
    def NickName(self):
      return self.config.nick_name.decode('utf-8')

    @NickName.setter
    def NickName(self, value):
      # TODO(jnewlin): Need some sanity here so the user can't enter
      # a value that hoses the file, like a carriage return or newline.
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

  def WriteNicknamesFile(self):
    """Write out the nicknames file for Sage."""
    if self.config.nicknames:
      with file(NICKFILE_TMP, 'w') as f:
        serials = []
        for nn in self.config.nicknames.itervalues():
          f.write('%s/nickname=%s\n' % (
              nn.SerialNumber, nn.config.nick_name.encode('unicode-escape')))
          serials.append(nn.SerialNumber)
        f.write('serials=%s\n' % ','.join(serials))
      os.rename(NICKFILE_TMP, NICKFILE)

  def _WriteOrRemove(self, filename, content):
    if content:
      tr.helpers.WriteFileAtomic(filename, content)
    else:
      # interpret empty content as "remove the file"
      tr.helpers.Unlink(filename)

  def CommitTransaction(self):
    """Write out the {Bluetooth, EAS} config files for Sage."""
    self.WriteNicknamesFile()

    if self.config.bt_devices is not None:
      self._WriteOrRemove(filename=BTDEVICES, content=self.config.bt_devices)
      self.config.bt_devices = None

    if self.config.bt_hh_devices is not None:
      self._WriteOrRemove(filename=BTHHDEVICES,
                          content=self.config.bt_hh_devices)
      self.config.bt_hh_devices = None

    if self.config.bt_config is not None:
      self._WriteOrRemove(filename=BTCONFIG, content=self.config.bt_config)
      self.config.bt_config = None

    if self.config.bt_nopairing is not None:
      content = 'nopair' if self.config.bt_nopairing else ''
      self._WriteOrRemove(filename=BTNOPAIRING, content=content)
      self.config.bt_nopairing = None

    if self.config.eas_code is not None:
      self._WriteOrRemove(filename=EASFIPSFILE, content=self.config.eas_code)
      self.config.eas_code = None

    if self.config.eas_service_addr is not None:
      self._WriteOrRemove(filename=EASADDRFILE,
                          content=self.config.eas_service_addr)
      self.config.eas_service_addr = None

    if self.config.eas_service_port is not None:
      self._WriteOrRemove(filename=EASPORTFILE,
                          content=self.config.eas_service_port)
      self.config.eas_service_port = None

    self.config_old = None

  @property
  def DevicePropertiesNumberOfEntries(self):
    return len(self.config.nicknames)

  def IterProperties(self):
    return self.config.nicknames.iteritems()

  def GetProperties(self, key):
    return self.config.nicknames[key]

  def SetProperties(self, key, child_object):
    child_object.parent = self
    self.config.nicknames[key] = child_object

  def DelProperties(self, key):
    del self.config.nicknames[key]

  def _ReadShortFile(self, filename):
    """Read a file into memory, return empty string if ENOEXIST."""
    try:
      with file(filename) as f:
        return f.read()
    except IOError as e:
      # If the file doesn't exist for some reason, just return an empty
      # string, otherwise throw the exception, which should get propagated
      # back to the ACS.
      if e.errno == errno.ENOENT:
        return ''
      raise

  @property
  def BtDevices(self):
    return self._ReadShortFile(BTDEVICES)

  @property
  def BtNoPairing(self):
    return os.access(BTNOPAIRING, os.R_OK)

  @BtNoPairing.setter
  def BtNoPairing(self, value):
    self.config.bt_nopairing = tr.cwmpbool.parse(value)

  @BtDevices.setter
  def BtDevices(self, value):
    self.config.bt_devices = value

  @property
  def BtHHDevices(self):
    return self._ReadShortFile(BTHHDEVICES)

  @BtHHDevices.setter
  def BtHHDevices(self, value):
    self.config.bt_hh_devices = value

  @property
  def BtConfig(self):
    return self._ReadShortFile(BTCONFIG)

  @BtConfig.setter
  def BtConfig(self, value):
    self.config.bt_config = value

  @property
  def EASFipsCode(self):
    return self._ReadShortFile(EASFIPSFILE)

  @EASFipsCode.setter
  def EASFipsCode(self, value):
    self.config.eas_code = str(value)

  @property
  def EASServiceAddress(self):
    return self._ReadShortFile(EASADDRFILE)

  @EASServiceAddress.setter
  def EASServiceAddress(self, value):
    self.config.eas_service_addr = str(value)

  @property
  def EASServicePort(self):
    return self._ReadShortFile(EASPORTFILE)

  @EASServicePort.setter
  def EASServicePort(self, value):
    self.config.eas_service_port = str(value)

  @property
  def EASHeartbeatTimestamp(self):
    try:
      with file(EASHEARTBEATFILE) as f:
        secs = float(f.read())
    except (IOError, OSError, ValueError):
      secs = 0.0
    return tr.cwmpdate.format(secs)


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
