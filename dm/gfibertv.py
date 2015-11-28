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

import bisect
import errno
import glob
import json
import os
import re
import subprocess
import weakref
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
DISK_SPACE_FILE = ['/tmp/dvr_space']
EASADDRFILE = ['/tmp/eas_service_address']
EASFIPSFILE = ['/tmp/eas_fips']
EASHEARTBEATFILE = ['/tmp/eas_heartbeat']
EASPORTFILE = ['/tmp/eas_service_port']
HNVRAM = ['hnvram']
MYNICKFILE = ['/config/nickname']
NICKFILE = ['/tmp/nicknames']
SAGEFILES = ['/app/sage/*.properties.default*', '/rw/sage/*.properties']
TCPALGORITHM = ['/config/tcp_congestion_control']
TVBUFFERADDRESS = ['/tmp/tv_buffer_address']
TVBUFFERKEY = ['/tmp/tv_buffer_key']
FROBNICASTADDRESS = ['/tmp/frobnicast_address']
FROBNICASTKEY = ['/tmp/frobnicast_key']
UICONTROLURLFILE = ['/tmp/oregano_url']
UI_IS_HTML = ['is-html-tv-ui']
UITYPEFILE = ['/tmp/ui/uitype']

RESTARTFROBCMD = ['restart', 'frobnicast']


def _SageEscape(s):
  """Encode a string so it's safe to include in a SageTV config file."""
  return re.sub(re.compile(r"[^\w'\- !@#$%^*_+,.&]", re.UNICODE), '_',
                s.strip()).encode('unicode-escape')


class GFiberTv(CATABASE.GFiberTV):
  """Implementation of x-gfibertv.xml."""

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
  TvBufferKey = tr.cwmptypes.Trigger(
      tr.cwmptypes.FileBacked(TVBUFFERKEY, tr.cwmptypes.String()))
  FrobnicastAddress = tr.cwmptypes.Trigger(
      tr.cwmptypes.FileBacked(FROBNICASTADDRESS, tr.cwmptypes.String()))
  FrobnicastKey = tr.cwmptypes.Trigger(
      tr.cwmptypes.FileBacked(FROBNICASTKEY, tr.cwmptypes.String()))

  def __init__(self, mailbox_url, my_serial=None):
    """GFiberTV object.

    Args:
      mailbox_url: XML-RPC endpoint for Mailbox access.
      my_serial: serial number of this device. A device nickname
        for this serial number will be written to MYNICKFILE.
    """
    super(GFiberTv, self).__init__()
    self.my_serial = my_serial
    self.DevicePropertiesList = {}
    self._rpcclient = xmlrpclib.ServerProxy(mailbox_url)
    self.Export(objects=['Config'])
    self._frobstatus = (False, None)

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
  def UiChoice(self):
    try:
      if subprocess.call(UI_IS_HTML) == 0:
        return 'oregano'
      else:
        return 'sage'
    except OSError:
      # This is not a TV platform.
      return 'none'

  @property
  def DvrSpace(self):
    return DvrSpace()

  @property
  def Config(self):
    return self._GetTreeTop()

  @tr.session.cache
  def _GetTreeTop(self):
    return _SageTvTree(self._rpcclient)

  class _DeviceProperties(CATABASE.GFiberTV.DeviceProperties):
    """Implementation of gfibertv.DeviceProperties."""

    NickName = tr.cwmptypes.TriggerString()
    SerialNumber = tr.cwmptypes.TriggerString()

    def __init__(self, parent, my_serial):
      super(GFiberTv._DeviceProperties, self).__init__()
      self.parent = weakref.ref(parent)
      self.my_serial = my_serial

    def Triggered(self):
      p = self.parent()
      if p:
        p.Triggered()

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

    # Start frobnicast if necessary
    status = (bool(self.FrobnicastKey and self.TvBufferKey),
              self.FrobnicastAddress)
    if status != self._frobstatus:
      subprocess.call(RESTARTFROBCMD, close_fds=True)
      self._frobstatus = status


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


class _SageProps(object):
  """A sorted list of (key, value) pairs straight out of Sage.properties.

  This is the base data structure that we read from the Sage.properties file.
  Everything else is just a view onto it.  We keep it sorted so that we can
  use binary searches to find items, insert items, and iterate over items
  that match a given prefix.
  """

  def __init__(self, data):
    self.data = data
    self.data.sort()
    self.cached_lists = {}
    self.cleaned = {}

    # Reverse lookup table for TR-069-compatible names back to SageTV names
    for key, unused_value in data:
      parts = key.split('/')
      clean_parts = [_Clean(p) for p in parts]
      p = ''
      for i in range(0, len(parts)):
        c = p + clean_parts[i] + '/'
        p += parts[i] + '/'
        if p != c:
          self.cleaned[c] = p

  def _Iter(self, prefix):
    assert prefix.endswith('/')
    i = bisect.bisect_left(self.data, (prefix,))
    end = bisect.bisect_left(self.data, (prefix[:-1]+chr(ord('/')+1),), i)
    for i in xrange(i, end):
      yield self.data[i]

  def Iter(self, prefix):
    if not prefix:
      return iter(self.data)
    else:
      return self._Iter(prefix)

  def __iter__(self):
    return iter(self.data)

  def __len__(self):
    return len(self.data)

  def get(self, key, defval):
    try:
      return self[key]
    except KeyError:
      return defval

  def __getitem__(self, key):
    start = bisect.bisect_left(self.data, (key,))
    if start < len(self.data) and self.data[start][0] == key:
      return self.data[start][1]
    else:
      raise KeyError(key)

  def __setitem__(self, key, value):
    value = str(value)  # the SageTV file only knows about strings
    start = bisect.bisect_left(self.data, (key,))
    if start < len(self.data) and self.data[start][0] == key:
      self.data[start] = (key, value)
    else:
      self.cached_lists.clear()
      self.data.insert(start, (key, value))

  def DeClean(self, clean_key):
    return self.cleaned.get(clean_key, clean_key)

  def GenCache(self, prefix):
    try:
      return self.cached_lists[prefix]
    except KeyError:
      prelen = len(prefix)
      out1 = set()
      out2 = set()
      for k, unused_v in self.Iter(prefix):
        sub_k = k[prelen:]
        if '/' in sub_k:
          # it has sub-items, so it must be an object, not a param
          out2.add(_Clean(sub_k.split('/', 1)[0]))
        else:
          out1.add(_Clean(sub_k))
      out = (out1, out2)
      self.cached_lists[prefix] = out
      return out


def _Clean(sagekey):
  return re.sub(r'[^\w/]', '_', sagekey)


def _ParseProps(lines):
  for line in lines:
    line = line.split('#', 1)[0]  # remove comments
    keyval = line.split('=', 1)
    if len(keyval) < 2: continue
    key, val = keyval
    key = re.sub(r'\\(.)', r'\1', key).strip()
    val = re.sub(r'\\(.)', r'\1', val).strip()
    yield key, val


def _SageTvTree(rpcclient):
  """Generates a toplevel _SageTvExporter."""

  print 'xmlrpc SaveProperties()'
  try:
    rpcclient.SaveProperties()
  except (xmlrpclib.expat.ExpatError,
          xmlrpclib.ProtocolError,
          xmlrpclib.Fault,
          IOError) as e:
    print 'xmlrpc: SaveProperties: %r' % e
    # not fatal, so continue anyway

  d = {}
  for g in SAGEFILES:
    for filename in glob.glob(g):
      try:
        lines = open(filename).readlines()
      except IOError as e:
        print e  # non-fatal, but interesting
        continue
      d.update(_ParseProps(lines))
  props = _SageProps(d.items())
  x = _SageTvExporter(rpcclient, props, '')
  return x


class _LyingSet(set):
  """A set object that lies about whether it contains the given key."""

  def __init__(self, contents, contains_func):
    set.__init__(self, contents)
    self.contains_func = contains_func

  def __contains__(self, key):
    return self.contains_func(key)


class _SageTvExporter(tr.core.AbstractExporter):
  """An auto-generated hierarchical view of the SageTV properties files.

  Querying SageTV itself is slow, so we do that only to flush the config file
  initially, and to actually change values.  For reading values, we just use
  the file contents, which are stored in the _SageTvProps object.

  The _SageTvExporter is a tr.core.AbstractExporter that is a thin wrapper
  on top of (some subsection of) the props.  The idea is the _SageTvExports
  objects can come and go without any significant re-parsing cost.

  Note: there are actually three levels SageTV looks at for its properties:
    0) Every get() call inside SageTV provides a default value.
    1) There's a read-only Sage.properties.default file with defaults.
    2) There's an read-write, initially empty, Sage.properties file with the
       values that differ from defaults.

  This implementation reads from #1 and #2.  There is no way to get the
  values from #0 as they exist at every call site inside SageTV (and the
  defaults might vary from one call site to another).  That restriction
  exists even if we use SageTV's GetProperty() RPC.
  """

  def __init__(self, rpcclient, props, realname):
    self._initialized = False
    self._rpcclient = rpcclient
    self._props = props
    self._realname = realname
    self._params = None
    self._subs = None
    super(_SageTvExporter, self).__init__()

  # This is used to convince tr.Handle that the requested parameter exists,
  # for all safe parameters.
  @property
  def export_params(self):
    return _LyingSet(self._props.GenCache(self._realname)[0],
                     self._IsSafeName)

  @property
  def export_objects(self):
    return self._props.GenCache(self._realname)[1]

  @property
  def export_object_lists(self):
    return set()

  def _FullName(self, name):
    return self._realname + name

  def _IsObject(self, name):
    return name in self.export_objects

  def _IsSafeName(self, key):
    return (not key.startswith('_') and
            key not in self.__dict__ and
            not hasattr(tr.core.Exporter, key) and
            key == _Clean(key))

  def _Set(self, realname, value):
    try:
      self._rpcclient.SetProperty(realname, str(value), '')
    except (xmlrpclib.Fault, xmlrpclib.ProtocolError, IOError), e:
      print 'xmlrpc: %s: %s' % (realname, e)
      raise ValueError('unable to set value: %s' % (e,))

  def __getattr__(self, name):
    if name.startswith('_') or not self._IsSafeName(name):
      raise AttributeError(name)
    fullname = self._FullName(name)
    if self._IsObject(name):
      return _SageTvExporter(self._rpcclient, self._props,
                             self._props.DeClean(fullname + '/'))
    else:
      # by request from ACS team, nonexistent params return empty not fault
      return self._props.get(fullname, '')

  def __setattr__(self, name, value):
    if name.startswith('_') or not self._IsSafeName(name):
      super(_SageTvExporter, self).__setattr__(name, value)
      return
    fullname = self._FullName(name)
    self._Set(self._props.DeClean(fullname + '/')[:-1], value)
    self._props[fullname] = value


if __name__ == '__main__':
  print tr.handle.DumpSchema(GFiberTv('http://localhost/'))
