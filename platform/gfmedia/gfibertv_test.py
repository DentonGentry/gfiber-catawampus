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

# unittest requires method names starting in 'test'
# pylint: disable-msg=C6409

"""Unit tests for gfibertv.py."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import os
import os.path
import shutil
import SimpleXMLRPCServer
import tempfile
import threading
import unittest
import xmlrpclib
import google3
import tr.cwmpdate
import tr.mainloop
import gfibertv


class TvPropertyRpcs(object):
  def __init__(self):
    self.running = True
    self.properties = {
        'Node1': {'Prop1': 'Prop1Value',
                  'Prop2': 'Prop2Value'},
        'Node2': {'Prop3': 'Prop3Value'}}

  def Quit(self):
    self.running = False
    return True

  def GetProperty(self, name, node):
    return self.properties[node][name]

  def SetProperty(self, name, value, node):
    self.properties[node][name] = value
    return ''

  def ListNodes(self):
    return self.properties.keys()

  def Ping(self):
    return ''


class TvXMLRPCServer(SimpleXMLRPCServer.SimpleXMLRPCServer):
  allow_reuse_address = 2


srv_port = 0
srv_cv = threading.Condition()


class XmlRpcThread(threading.Thread):
  def run(self):
    self.tv = TvPropertyRpcs()
    xmlrpcsrv = TvXMLRPCServer(('localhost', 0))
    global srv_port
    _, srv_port = xmlrpcsrv.server_address
    xmlrpcsrv.logRequests = False
    xmlrpcsrv.register_introspection_functions()
    xmlrpcsrv.register_instance(self.tv)
    srv_cv.acquire()
    srv_cv.notify()
    srv_cv.release()
    while self.tv.running:
      xmlrpcsrv.handle_request()
    xmlrpcsrv.server_close()


class GfiberTvTests(unittest.TestCase):
  """Tests for gfibertv.py."""

  def setUp(self):
    srv_cv.acquire()
    self.server_thread = XmlRpcThread()
    self.server_thread.start()
    srv_cv.wait()

    self.loop = tr.mainloop.MainLoop()

    self.DISK_SPACE_FILE = gfibertv.DISK_SPACE_FILE
    gfibertv.DISK_SPACE_FILE = ['testdata/gfibertv/dvr_space']

    self.tmpdir = tempfile.mkdtemp()
    (nick_file_handle, self.nick_file_name) = tempfile.mkstemp(dir=self.tmpdir)
    (tmp_file_handle, self.tmp_file_name) = tempfile.mkstemp(dir=self.tmpdir)
    os.close(nick_file_handle)
    os.close(tmp_file_handle)
    gfibertv.NICKFILE[0] = self.nick_file_name
    self.EASHEARTBEATFILE = gfibertv.EASHEARTBEATFILE[0]

    (btdevices_handle, self.btdevices_fname) = tempfile.mkstemp(dir=self.tmpdir)
    os.close(btdevices_handle)
    gfibertv.BTDEVICES[0] = self.btdevices_fname

    (bthh_handle, self.bthhdevices_fname) = tempfile.mkstemp(dir=self.tmpdir)
    os.close(bthh_handle)
    gfibertv.BTHHDEVICES[0] = self.bthhdevices_fname

    (btconfig_handle, self.btconfig_fname) = tempfile.mkstemp(dir=self.tmpdir)
    os.close(btconfig_handle)
    gfibertv.BTCONFIG[0] = self.btconfig_fname

    (btnopair_handle, self.btnopair_fname) = tempfile.mkstemp(dir=self.tmpdir)
    os.close(btnopair_handle)
    os.unlink(self.btnopair_fname)
    gfibertv.BTNOPAIRING[0] = self.btnopair_fname

    (easfips_handle, self.easfips_fname) = tempfile.mkstemp(dir=self.tmpdir)
    os.close(easfips_handle)
    os.unlink(self.easfips_fname)
    gfibertv.EASFIPSFILE[0] = self.easfips_fname

    (easaddr_handle, self.easaddr_fname) = tempfile.mkstemp(dir=self.tmpdir)
    os.close(easaddr_handle)
    os.unlink(self.easaddr_fname)
    gfibertv.EASADDRFILE[0] = self.easaddr_fname

    (easport_handle, self.easport_fname) = tempfile.mkstemp(dir=self.tmpdir)
    os.close(easport_handle)
    os.unlink(self.easport_fname)
    gfibertv.EASPORTFILE[0] = self.easport_fname

  def tearDown(self):
    xmlrpclib.ServerProxy('http://localhost:%d' % srv_port).Quit()
    self.server_thread.join()
    shutil.rmtree(self.tmpdir)

  def testValidate(self):
    tv = gfibertv.GFiberTv('http://localhost:%d' % srv_port)
    tv.Mailbox.Node = 'Node1'
    tv.Mailbox.Name = 'Prop1'
    tv.ValidateExports()

  def testGetProperties(self):
    tvrpc = gfibertv.Mailbox('http://localhost:%d' % srv_port)
    tvrpc.Node = 'Node1'
    tvrpc.Name = 'Prop1'
    self.assertEqual(tvrpc.Value, 'Prop1Value')
    tvrpc.Name = 'Prop2'
    self.assertEqual(tvrpc.Value, 'Prop2Value')
    tvrpc.Node = 'Node2'
    tvrpc.Name = 'Prop3'
    self.assertEqual(tvrpc.Value, 'Prop3Value')
    tvrpc.Name = 'Prop4'
    self.assertRaises(IndexError, lambda: tvrpc.Value)
    tvrpc.Node = 'Node3'
    self.assertRaises(IndexError, lambda: tvrpc.Value)

  def testGetPropertiesProtocolError(self):
    tvrpc = gfibertv.Mailbox('http://localhost:2')
    tvrpc.Node = 'Node1'
    tvrpc.Name = 'Prop1'
    self.assertRaises(IndexError, lambda: tvrpc.Value)

  def testSetProperties(self):
    tvrpc = gfibertv.Mailbox('http://localhost:%d' % srv_port)
    tvrpc.Node = 'Node1'
    tvrpc.Name = 'Prop1'
    tvrpc.Value = 'Prop1NewValue'
    self.assertEqual(tvrpc.Value, 'Prop1NewValue')
    tvrpc.Name = 'Prop4'
    self.assertRaises(IndexError, lambda: tvrpc.Value)
    tvrpc.Node = 'Node3'
    self.assertRaises(IndexError, lambda: tvrpc.Value)

  def testSetPropertiesProtocolError(self):
    tvrpc = gfibertv.Mailbox('http://localhost:2')
    tvrpc.Node = 'Node1'
    tvrpc.Name = 'Prop1'
    self.assertRaises(IndexError, lambda: setattr(tvrpc, 'Value', 1))

  def testNodeList(self):
    tvrpc = gfibertv.Mailbox('http://localhost:%d' % srv_port)
    self.assertEqual(tvrpc.NodeList, 'Node1, Node2')

  def testListManipulation(self):
    gftv = gfibertv.GFiberTv('http://localhost:%d' % srv_port)
    self.assertEqual(0, gftv.DevicePropertiesNumberOfEntries)
    idx, newobj = gftv.AddExportObject('DeviceProperties', None)
    idx = int(idx)
    self.assertEqual(1, gftv.DevicePropertiesNumberOfEntries)
    self.assertEqual(newobj, gftv.DevicePropertiesList[idx])
    self.assertEqual(None, gftv.DevicePropertiesList[idx].NickName)

    idx2, newobj = gftv.AddExportObject('DeviceProperties', None)
    idx2 = int(idx2)
    idx3, newobj = gftv.AddExportObject('DeviceProperties', None)
    idx3 = int(idx3)

    gftv.DevicePropertiesList[idx].NickName = 'testroom'
    gftv.DevicePropertiesList[idx].SerialNumber = '12345'

    uni_name = u'\u212ced\nroom\n\r!'
    gftv.DevicePropertiesList[idx2].NickName = uni_name
    gftv.DevicePropertiesList[idx2].SerialNumber = '56789'

    gftv.DevicePropertiesList[idx3].NickName = "Peter's Room"
    gftv.DevicePropertiesList[idx3].SerialNumber = '23456'

    self.loop.RunOnce()

    # read the test file back in.
    lines = open(gfibertv.NICKFILE[0], 'r').readlines()
    last_line = lines and lines[-1].strip()

    self.assertTrue('12345/nickname=testroom\n' in lines)
    self.assertTrue('56789/nickname=\\u212ced_room__!\n' in lines)
    self.assertTrue("23456/nickname=Peter's Room\n" in lines)
    self.assertTrue(last_line.startswith('serials='))
    split1 = last_line.split('=')
    self.assertEqual(2, len(split1))
    split2 = split1[1].split(',')
    self.assertTrue('12345' in split2)
    self.assertTrue('56789' in split2)
    self.assertTrue('23456' in split2)

  def testBtFiles(self):
    gftv = gfibertv.GFiberTv('http://localhost:%d' % srv_port)
    self.loop.RunOnce()

    self.assertEqual('', gftv.BtDevices)
    self.assertEqual('', gftv.BtHHDevices)
    self.assertEqual('', gftv.BtConfig)

    devices1 = 'This is a test'
    devices2 = 'devices test 2'
    hhdevices = 'hhdevice str\nwith a newline'
    config = 'btconfig str'

    gftv.BtDevices = devices1
    self.loop.RunOnce()
    self.assertEqual(devices1, gftv.BtDevices)
    self.assertEqual(open(self.btdevices_fname).read(), devices1 + '\n')
    self.assertEqual('', gftv.BtHHDevices)
    self.assertEqual(open(self.bthhdevices_fname).read(), '')
    self.assertEqual('', gftv.BtConfig)
    self.assertEqual(open(self.btconfig_fname).read(), '')

    gftv.BtDevices = devices2
    gftv.BtHHDevices = hhdevices
    gftv.BtConfig = config
    self.loop.RunOnce()
    self.assertEqual(devices2, gftv.BtDevices)
    self.assertEqual(open(self.btdevices_fname).read(), devices2 + '\n')
    self.assertEqual(hhdevices, gftv.BtHHDevices)
    self.assertEqual(open(self.bthhdevices_fname).read(), hhdevices + '\n')
    self.assertEqual(config, gftv.BtConfig)
    self.assertEqual(open(self.btconfig_fname).read(), config + '\n')

  def testNoPairing(self):
    gftv = gfibertv.GFiberTv('http://localhost:%d' % srv_port)
    self.loop.RunOnce()
    self.assertFalse(gftv.BtNoPairing)
    self.assertFalse(os.path.exists(self.btnopair_fname))

    gftv.BtNoPairing = True
    self.loop.RunOnce()
    self.assertTrue(gftv.BtNoPairing)
    self.assertTrue(os.path.exists(self.btnopair_fname))

    # Make sure setting to True works if it is already true.
    gftv.BtNoPairing = True
    self.loop.RunOnce()
    self.assertTrue(gftv.BtNoPairing)
    self.assertTrue(os.path.exists(self.btnopair_fname))

    gftv.BtNoPairing = False
    self.loop.RunOnce()
    self.assertFalse(gftv.BtNoPairing)
    self.assertFalse(os.path.exists(self.btnopair_fname))

    # Make sure setting to False works if it is already false.
    gftv.BtNoPairing = False
    self.loop.RunOnce()
    self.assertFalse(gftv.BtNoPairing)
    self.assertFalse(os.path.exists(self.btnopair_fname))

  def testEASHeartbeatTimestamp(self):
    gftv = gfibertv.GFiberTv('http://localhost:%d' % srv_port)
    gfibertv.EASHEARTBEATFILE[0] = 'testdata/gfibertv/eas_heartbeat'
    self.assertEqual(tr.cwmpdate.format(gftv.EASHeartbeatTimestamp),
                     '2012-11-09T22:26:40Z')
    gfibertv.EASHEARTBEATFILE[0] = '/path/to/nonexistant'
    self.assertEqual(tr.cwmpdate.format(gftv.EASHeartbeatTimestamp),
                     '0001-01-01T00:00:00Z')
    gfibertv.EASHEARTBEATFILE[0] = 'testdata/gfibertv/eas_heartbeat.bad'
    self.assertEqual(tr.cwmpdate.format(gftv.EASHeartbeatTimestamp),
                     '0001-01-01T00:00:00Z')

  def testEASFipsCode(self):
    gftv = gfibertv.GFiberTv('http://localhost:%d' % srv_port)
    gftv.EASFipsCode = 'FIPS Code'
    self.loop.RunOnce()
    self.assertEqual(open(self.easfips_fname).read(), 'FIPS Code\n')

  def testEASFipsServiceAddress(self):
    gftv = gfibertv.GFiberTv('http://localhost:%d' % srv_port)
    gftv.EASServiceAddress = 'Service Addr'
    self.loop.RunOnce()
    self.assertEqual(open(self.easaddr_fname).read(), 'Service Addr\n')

  def testEASFipsServicePort(self):
    gftv = gfibertv.GFiberTv('http://localhost:%d' % srv_port)
    gftv.EASServicePort = 'Service Port'
    self.loop.RunOnce()
    self.assertEqual(open(self.easport_fname).read(), 'Service Port\n')

  def testDvrSpace(self):
    gftv = gfibertv.GFiberTv('http://localhost:%d' % srv_port)
    dvrspace = gftv.DvrSpace
    self.assertEqual(dvrspace.PermanentFiles, 10)
    self.assertEqual(dvrspace.PermanentMBytes, 1)
    self.assertEqual(dvrspace.TransientFiles, 20)
    self.assertEqual(dvrspace.TransientMBytes, 2)


if __name__ == '__main__':
  unittest.main()
