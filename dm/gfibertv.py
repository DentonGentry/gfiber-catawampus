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
# pylint:disable=invalid-name
# pylint:disable=protected-access
#
"""Implement handling for the X_GOOGLE-COM_GFIBERTV vendor data model."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import errno
import glob
import json
import os
import re
import subprocess
import xmlrpclib
import google3
import tr.api
import tr.core
import tr.cwmpbool
import tr.cwmpdate
import tr.cwmptypes
import tr.handle
import tr.helpers
import tr.mainloop
import tr.session
import tr.x_catawampus_tr181_2_0

BASE = tr.x_catawampus_tr181_2_0.X_CATAWAMPUS_ORG_Device_v2_0
CATABASE = BASE.Device.X_CATAWAMPUS_ORG

# These are lists so list[0] can be reassigned in a unit test to affect
# the operation of tr.cwmptypes.FileBacked.
BTDEVICES = ['/user/bsa/bt_devices.xml']
BTHHDEVICES = ['/user/bsa/bt_hh_devices.xml']
BTCONFIG = ['/user/bsa/bt_config.xml']
BTNOPAIRING = ['/user/bsa/nopairing']
DISK_SPACE_FILE = ['/tmp/dvr_space']
EASADDRFILE = ['/tmp/eas_service_address']
EASFIPSFILE = ['/tmp/eas_fips']
EASHEARTBEATFILE = ['/tmp/eas_heartbeat']
EASPORTFILE = ['/tmp/eas_service_port']
HNVRAM = ['hnvram']
MYNICKFILE = ['/config/nickname']
NICKFILE = ['/tmp/nicknames']
SAGEFILES = ['/app/sage/*.properties.default*', '/rw/sage/*.properties']
UICONTROLURLFILE = ['/tmp/oregano_url']
TCPALGORITHM = ['/config/tcp_congestion_control']
TVBUFFERADDRESS = ['/tmp/tv_buffer_address']
TVBUFFERKEY = ['/tmp/tv_buffer_key']
UICONTROLURLFILE = ['/tmp/oregano_url']
UITYPEFILE = ['/tmp/ui/uitype']


def _SageEscape(s):
  """Encode a string so it's safe to include in a SageTV config file."""
  return re.sub(re.compile(r"[^\w'\- !@#$%^*_+,.&]", re.UNICODE), '_',
                s.strip()).encode('unicode-escape')


class GFiberTv(CATABASE.GFiberTV):
  """Implementation of x-gfibertv.xml."""
  BtConfig = tr.cwmptypes.FileBacked(BTCONFIG, tr.cwmptypes.String())
  BtDevices = tr.cwmptypes.FileBacked(BTDEVICES, tr.cwmptypes.String())
  BtHHDevices = tr.cwmptypes.FileBacked(BTHHDEVICES, tr.cwmptypes.String())
  BtNoPairing = tr.cwmptypes.FileBacked(BTNOPAIRING, tr.cwmptypes.String())

  @BtNoPairing.validator
  def BtNoPairing(self, value):
    # tr.cwmptypes.Bool is picky about parsing, and we don't want that when
    # reading possibly-invalid data from a file, so we use tr.cwmptypes.String
    # and parse it ourselves.
    if not value or value == 'false' or value == 'False' or value == '0':
      return ''
    else:
      return True

  EASFipsCode = tr.cwmptypes.FileBacked(EASFIPSFILE, tr.cwmptypes.String())
  EASServiceAddress = tr.cwmptypes.FileBacked(
      EASADDRFILE, tr.cwmptypes.String())
  EASServicePort = tr.cwmptypes.FileBacked(EASPORTFILE, tr.cwmptypes.String())
  f = tr.cwmptypes.FileBacked(EASHEARTBEATFILE, tr.cwmptypes.Date())
  EASHeartbeatTimestamp = tr.cwmptypes.ReadOnly(f)
  TcpAlgorithm = tr.cwmptypes.FileBacked(TCPALGORITHM, tr.cwmptypes.String())
  UiControlUrl = tr.cwmptypes.FileBacked(
      UICONTROLURLFILE, tr.cwmptypes.String())
  TvBufferAddress = tr.cwmptypes.FileBacked(
      TVBUFFERADDRESS, tr.cwmptypes.String())
  TvBufferKey = tr.cwmptypes.FileBacked(TVBUFFERKEY, tr.cwmptypes.String())

  def __init__(self, mailbox_url, my_serial=None):
    """GFiberTV object.

    Args:
      mailbox_url: XML-RPC endpoint for Mailbox access.
      my_serial: serial number of this device. A device nickname
        for this serial number will be written to MYNICKFILE.
    """
    super(GFiberTv, self).__init__()
    self.my_serial = my_serial
    self.Mailbox = Mailbox(mailbox_url)
    self.DevicePropertiesList = {}
    self._rpcclient = xmlrpclib.ServerProxy(mailbox_url)

    # TODO(apenwarr): Maybe remove this eventually.
    #  Right now the storage box has an API, but TV boxes don't, so we
    #  can't control a TV box directly; we have to control it through the
    #  storage box in the Node list.  This makes it a bit messy to configure
    #  with the ACS since the configuration keys need to refer to individual
    #  devices. If we add a server on the TV boxes, we can eventually remove
    #  this part and leave only Config.
    self.NodeList = tr.core.AutoDict('NodeList',
                                     iteritems=self._ListNodes,
                                     getitem=self._GetNode)
    self.Export(objects=['Config'], lists=['Node'])

  def GetUiType(self):
    cmd = HNVRAM + ['-q', '-r', 'UITYPE']
    devnull = open('/dev/null', 'w')
    try:
      hnvram = subprocess.Popen(cmd, stdin=devnull, stderr=devnull,
                                stdout=subprocess.PIPE)
      out, _ = hnvram.communicate()
      if hnvram.returncode != 0:
        return 'Unknown'
    except OSError:
      return 'Unknown'
    return out.strip()

  @tr.mainloop.WaitUntilIdle
  def _CreateIfNotExist(self, filename, content):
    """Create filename with content, but only if it does not already exist.

    If the system has already booted and chosen a uitype, don't disrupt
    that choice. If the system is waiting for the uitype to be set, then
    set it.

    Args:
      filename: file to write to
      content: content to write to filename
    """
    try:
      fd = os.open(UITYPEFILE[0], os.O_WRONLY | os.O_CREAT | os.O_EXCL)
      f = os.fdopen(fd, 'w')
      f.write(content)
      f.close()
    except OSError as e:
      if e.errno != errno.EEXIST:
        raise

  def SetUiType(self, value):
    cmd = HNVRAM + ['-w', 'UITYPE=' + str(value)]
    if subprocess.call(cmd) != 0:
      raise OSError('hnvram write failed')
    self._CreateIfNotExist(UITYPEFILE[0], str(value))

  UiType = property(GetUiType, SetUiType, None, 'UiType')

  @property
  def DvrSpace(self):
    return DvrSpace()

  @property
  def Config(self):
    return self._GetNode('')

  def _ListNodes(self):
    try:
      nodes = self._rpcclient.ListNodes()
    except IOError, e:
      if e.errno == errno.ECONNREFUSED:
        return []
      else:
        raise IndexError('Failure listing nodes: %s' % e)
    except (xmlrpclib.Fault, xmlrpclib.ProtocolError), e:
      raise IndexError('Failure listing nodes: %s' % e)
    return [(str(node), self._GetNode(node)) for node in nodes]

  @tr.session.cache
  def _GetNode(self, name):
    top = _PopulateTree(self._rpcclient, name, '')
    _ExportTree(top)
    return top

  class _DeviceProperties(CATABASE.GFiberTV.DeviceProperties):
    """Implementation of gfibertv.DeviceProperties."""

    NickName = tr.cwmptypes.TriggerString()
    SerialNumber = tr.cwmptypes.TriggerString()

    def __init__(self, parent, my_serial):
      super(GFiberTv._DeviceProperties, self).__init__()
      self.parent = parent
      self.my_serial = my_serial
      self.Triggered = self.parent.Triggered

  def DeviceProperties(self):
    """Default constructor for new elements of DevicePropertiesList.

    Called automatically by the tr.core API to add new entries. Normally
    the _DeviceProperties class would just be called DeviceProperties and
    tr.core would instantiate it, but we want to pass it a parent= value
    to the constructor, so we do this trick instead.

    Returns:
      gfibertv.DeviceProperties
    """
    return self._DeviceProperties(parent=self, my_serial=self.my_serial)

  @property
  def DevicePropertiesNumberOfEntries(self):
    return len(self.DevicePropertiesList.keys())

  @tr.mainloop.WaitUntilIdle
  def Triggered(self):
    # write the SageTV nicknames file
    with tr.helpers.AtomicFile(NICKFILE[0]) as f:
      serials = []
      for device in self.DevicePropertiesList.values():
        if device.SerialNumber and device.NickName:
          f.write('%s/nickname=%s\n' % (_SageEscape(device.SerialNumber),
                                        _SageEscape(device.NickName)))
          if device.SerialNumber == self.my_serial:
            with tr.helpers.AtomicFile(MYNICKFILE[0]) as sf:
              sf.write(device.NickName.encode('utf-8'))
          serials.append(device.SerialNumber)
      f.write('serials=%s\n' % ','.join(_SageEscape(i) for i in serials))


class DvrSpace(CATABASE.GFiberTV.DvrSpace):
  """X_GOOGLE_COM_GFIBERTV.DvrSpace.

  Ephemeral object to export information from /tmp/dvr_space.
  """

  PermanentMBytes = tr.cwmptypes.ReadOnlyInt(-1)
  PermanentFiles = tr.cwmptypes.ReadOnlyInt(-1)
  TransientMBytes = tr.cwmptypes.ReadOnlyInt(-1)
  TransientFiles = tr.cwmptypes.ReadOnlyInt(-1)

  def __init__(self):
    super(DvrSpace, self).__init__()
    data = dict()
    for filename in DISK_SPACE_FILE:
      self._LoadJSON(filename, data)
    mbytes = data.get('permanentSize', -1000000)
    type(self).PermanentMBytes.Set(self, mbytes / 1000000)
    type(self).PermanentFiles.Set(self, data.get('permanentFiles', -1))
    mbytes = data.get('transientSize', -1000000)
    type(self).TransientMBytes.Set(self, mbytes / 1000000)
    type(self).TransientFiles.Set(self, data.get('transientFiles', -1))

  def _LoadJSON(self, filename, data):
    """Populate data with fields read from the JSON file at filename."""
    try:
      d = json.load(open(filename))
      data.update(d)
    except IOError:
      # Sage might not be running yet
      pass
    except (ValueError, KeyError) as e:
      # ValueError - JSON file is malformed and cannot be decoded
      # KeyError - Decoded JSON file doesn't contain the required fields.
      print('DvrSpace: Failed to read stats from file {0}, '
            'error = {1}'.format(filename, e))


class Mailbox(CATABASE.GFiberTV.Mailbox):
  """Getter/setter for individual values in the SageTV configuration.

  You set Node the node name, set Name to the config key you want to get/set,
  and then get/set the Value field to read or write the actual value in the
  configuration file.

  Note: this API is deprecated. Consider using the PropList (GFiberTv.Config)
  instead.
  """

  Node = tr.cwmptypes.String('')
  Name = tr.cwmptypes.String('')

  def __init__(self, url):
    super(Mailbox, self).__init__()
    self.rpcclient = xmlrpclib.ServerProxy(url)

  @property
  def Value(self):
    if not self.Name:
      return None
    try:
      return str(self.rpcclient.GetProperty(self.Name, self.Node))
    except xmlrpclib.Fault:
      raise IndexError('No such Property %s:%s' % (self.Node, self.Name))
    except (xmlrpclib.ProtocolError, IOError):
      raise IndexError(
          'Unable to access Property %r:%r' % (self.Node, self.Name))

  @Value.setter
  def Value(self, value):
    try:
      return str(self.rpcclient.SetProperty(self.Name, str(value), self.Node))
    except xmlrpclib.Fault:
      raise IndexError('No such Property %s:%s' % (self.Node, self.Name))
    except (xmlrpclib.ProtocolError, IOError):
      raise IndexError(
          'Unable to access Property %r:%r' % (self.Node, self.Name))

  @property
  def NodeList(self):
    try:
      nodes = self.rpcclient.ListNodes()
      if nodes and isinstance(nodes, basestring):
        # if there is only one node, xmlrpclib helpfully returns a string
        # instead of a list.
        nodes = [nodes]
      return str(', '.join(nodes))
    except (xmlrpclib.Fault, xmlrpclib.ProtocolError, IOError), e:
      print 'gfibertv.NodeList: %s' % e
      return ''


class _LyingSet(set):
  """A set object that always lies and says it contains the given key."""

  def __init__(self, contents, contains_func):
    set.__init__(self, contents)
    self.contains_func = contains_func

  def __contains__(self, key):
    return self.contains_func(key)


class PropList(tr.core.AbstractExporter):
  """An auto-generated list of properties in the SageTV database."""

  def __init__(self, rpcclient, node, realname):
    self._initialized = False
    self._rpcclient = rpcclient
    self._node = node
    self._realname = realname
    self._params = {}
    self._subs = {}
    self._GetExport = True
    super(PropList, self).__init__()
    self._initialized = True

  # This is used to convince tr.Handle that the requested parameter exists,
  # for all safe parameters.
  @property
  def export_params(self):
    return _LyingSet(self._params.keys(), self._IsSafeName)

  @property
  def export_objects(self):
    return self._subs.keys()

  @property
  def export_object_lists(self):
    return set()

  def _IsSafeName(self, key):
    return (not key.startswith('_') and
            key not in self.__dict__ and
            not hasattr(tr.core.Exporter, key))

  def _Get(self, realname):
    # TODO(apenwarr): use a single API call to get all the names and values,
    #  then just cache them.  Retrieving them one at a time from SageTV
    #  is very slow.
    print 'xmlrpc getting %r' % realname
    try:
      return str(self._rpcclient.GetProperty(realname, self._node))
    except xmlrpclib.expat.ExpatError as e:
      # TODO(apenwarr): SageTV produces invalid XML.
      # ...if the value contains <> characters, for example.
      print 'Expat decode error: %s' % e
      return None
    except xmlrpclib.Fault as e:
      # by request from ACS team, nonexistent params return empty not fault
      param = '%s/%s' % (self._node, realname)
      print 'xmlrpc: no such parameter %r: returning empty string' % param
      return ''
    except (xmlrpclib.ProtocolError, IOError) as e:
      print 'xmlrpc: %s/%s: %r' % (self._node, realname, e)
      raise AttributeError('unable to get value %r' % realname)

  def _Set(self, realname, value):
    try:
      return str(self._rpcclient.SetProperty(realname, str(value), self._node))
    except (xmlrpclib.Fault, xmlrpclib.ProtocolError, IOError), e:
      print 'xmlrpc: %s/%s: %s' % (self._node, realname, e)
      raise ValueError('unable to set value: %s' % (e,))

  def __getattr__(self, name):
    if name.startswith('_') or not self._IsSafeName(name):
      raise AttributeError(name)
    elif name in self._subs:
      return self._subs[name]
    elif name in self._params:
      return self._Get(self._params[name])
    else:
      fullname = name
      if self._realname: fullname = self._realname + '/' + name
      return self._Get(fullname)

  def __setattr__(self, name, value):
    if name.startswith('_') or not self._IsSafeName(name):
      return super(PropList, self).__setattr__(name, value)
    elif name in self._params:
      return self._Set(self._params[name], value)
    elif self._initialized:
      # once object is initialized, unknown parameters go to XML-RPC not local
      fullname = str(name)
      if self._realname: fullname = self._realname + '/' + name
      self._params[name] = fullname
      return self._Set(fullname, value)
    else:
      return super(PropList, self).__setattr__(name, value)


def _PopulateTree(rpcclient, nodename, topname):
  """Populate the list of available objects using the config file contents."""
  # TODO(apenwarr): add a server API to get the actual property list.
  #  Then use it here. Reading it from the file is kind of cheating.
  top = PropList(rpcclient, nodename, topname)
  for g in SAGEFILES:
    for filename in glob.glob(g):
      try:
        lines = open(filename).readlines()
      except IOError as e:
        print e  # non-fatal, but interesting
        continue
      for line in lines:
        line = line.split('#', 1)[0]  # remove comments
        line = line.split('=', 1)[0]  # remove =value from key=value
        line = line.strip()
        realname = line.strip()
        if topname: realname = topname + '/' + realname
        # Find or create the intermediate PropLists leading up to this leaf
        if realname:
          clean = re.sub(r'[^\w/]', '_', realname)
          parts = clean.split('/')
          obj = top
          for i, part in enumerate(parts[:-1]):
            if part not in obj._subs:
              obj._subs[part] = PropList(rpcclient, nodename,
                                         '/'.join(parts[:i+1]))
            obj = obj._subs[part]
          obj._params[parts[-1]] = '/'.join(parts)
  return top


def _ExportTree(obj):
  # Once the tree is populated, this function recursively registers it
  # with tr.core.Exporter.
  for i in obj._subs:
    if i in obj._params:
      del obj._params[i]
  for i in obj._subs.values():
    _ExportTree(i)


if __name__ == '__main__':
  print tr.handle.DumpSchema(GFiberTv('http://localhost/'))
