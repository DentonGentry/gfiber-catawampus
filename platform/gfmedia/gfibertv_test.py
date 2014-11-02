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
# pylint:disable=invalid-name

"""Unit tests for gfibertv.py."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import os
import os.path
import shutil
import SimpleXMLRPCServer
import tempfile
import threading
import xmlrpclib
import google3
from tr.wvtest import unittest
import tr.cwmpdate
import tr.helpers
import tr.mainloop
import gfibertv


TvProperties = {}

class TvPropertyRpcs(object):
  def __init__(self):
    self.running = True

  def Quit(self):
    self.running = False
    return True

  def GetProperty(self, name, node):
    return TvProperties[node][name]

  def SetProperty(self, name, value, node):
    TvProperties[node][name] = value
    return ''

  def ListNodes(self):
    return TvProperties.keys()

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
    TvProperties.clear()
    TvProperties['Node1'] = {'Prop1': 'Prop1Value', 'Prop2': 'Prop2Value'}
    TvProperties['Node2'] = {'Prop3': 'Prop3Value'}
    srv_cv.acquire()
    self.server_thread = XmlRpcThread()
    self.server_thread.start()
    srv_cv.wait()

    self.loop = tr.mainloop.MainLoop()

    self.old_DISK_SPACE_FILE = gfibertv.DISK_SPACE_FILE
    gfibertv.DISK_SPACE_FILE = ['testdata/gfibertv/dvr_space']
    self.old_HNVRAM = gfibertv.HNVRAM

    self.tmpdir = tempfile.mkdtemp()
    self.nick_file_name = os.path.join(self.tmpdir, 'NICKFILE')
    gfibertv.NICKFILE[0] = self.nick_file_name
    self.my_nick_file_name = os.path.join(self.tmpdir, 'MYNICKFILE')
    gfibertv.MYNICKFILE[0] = self.my_nick_file_name
    self.btdevices_fname = os.path.join(self.tmpdir, 'BTDEVICES')
    gfibertv.BTDEVICES[0] = self.btdevices_fname
    self.bthhdevices_fname = os.path.join(self.tmpdir, 'BTHHDEVICES')
    gfibertv.BTHHDEVICES[0] = self.bthhdevices_fname
    self.btconfig_fname = os.path.join(self.tmpdir, 'BTCONFIG')
    gfibertv.BTCONFIG[0] = self.btconfig_fname
    self.btnopair_fname = os.path.join(self.tmpdir, 'BTNOPAIRING')
    gfibertv.BTNOPAIRING[0] = self.btnopair_fname
    self.easfips_fname = os.path.join(self.tmpdir, 'EASFIPSFILE')
    gfibertv.EASFIPSFILE[0] = self.easfips_fname
    self.easaddr_fname = os.path.join(self.tmpdir, 'EASADDRFILE')
    gfibertv.EASADDRFILE[0] = self.easaddr_fname
    self.easport_fname = os.path.join(self.tmpdir, 'EASPORTFILE')
    gfibertv.EASPORTFILE[0] = self.easport_fname
    self.tcpalgorithm_fname = os.path.join(self.tmpdir, 'TCPALGORITHM')
    gfibertv.TCPALGORITHM[0] = self.tcpalgorithm_fname
    self.uicontrol_fname = os.path.join(self.tmpdir, 'UICONTROLURLFILE')
    gfibertv.UICONTROLURLFILE[0] = self.uicontrol_fname
    self.uitype_fname = os.path.join(self.tmpdir, 'UITYPEFILE')
    gfibertv.UITYPEFILE[0] = self.uitype_fname
    self.tvbufferadddress_fname = os.path.join(self.tmpdir, 'TVBUFFERADDRESS')
    gfibertv.TVBUFFERADDRESS[0] = self.tvbufferadddress_fname
    self.tvbufferkey_fname = os.path.join(self.tmpdir, 'TVBUFFERKEY')
    gfibertv.TVBUFFERKEY[0] = self.tvbufferkey_fname

  def tearDown(self):
    xmlrpclib.ServerProxy('http://localhost:%d' % srv_port).Quit()
    self.server_thread.join()
    shutil.rmtree(self.tmpdir)
    gfibertv.DISK_SPACE_FILE = self.old_DISK_SPACE_FILE
    gfibertv.HNVRAM = self.old_HNVRAM

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

  def testSetPropertyInteger(self):
    tvrpc = gfibertv.Mailbox('http://localhost:%d' % srv_port)
    tvrpc.Node = 'Node1'
    tvrpc.Name = 'Prop1'
    tvrpc.Value = 1
    # RPC turns value into a string
    self.assertEqual(TvProperties['Node1']['Prop1'], '1')

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
    idx4, newobj = gftv.AddExportObject('DeviceProperties', None)
    idx4 = int(idx4)

    gftv.DevicePropertiesList[idx].NickName = 'testroom'
    gftv.DevicePropertiesList[idx].SerialNumber = '12345'

    uni_name = u'\u212ced\nroom\n\r!'
    gftv.DevicePropertiesList[idx2].NickName = uni_name
    gftv.DevicePropertiesList[idx2].SerialNumber = '56789'

    gftv.DevicePropertiesList[idx3].NickName = "Peter's Room"
    gftv.DevicePropertiesList[idx3].SerialNumber = '23456'

    gftv.DevicePropertiesList[idx4].NickName = "War & Peace"
    gftv.DevicePropertiesList[idx4].SerialNumber = '8675309'

    self.loop.RunOnce()

    # read the test file back in.
    lines = open(gfibertv.NICKFILE[0], 'r').readlines()
    last_line = lines and lines[-1].strip()

    self.assertTrue('12345/nickname=testroom\n' in lines)
    self.assertTrue('56789/nickname=\\u212ced_room__!\n' in lines)
    self.assertTrue("23456/nickname=Peter's Room\n" in lines)
    self.assertTrue("8675309/nickname=War & Peace\n" in lines)
    self.assertTrue(last_line.startswith('serials='))
    split1 = last_line.split('=')
    self.assertEqual(2, len(split1))
    split2 = split1[1].split(',')
    self.assertTrue('12345' in split2)
    self.assertTrue('56789' in split2)
    self.assertTrue('23456' in split2)
    self.assertTrue('8675309' in split2)

  def testMyNickname(self):
    mailbox_url = 'http://localhost:%d' % srv_port
    my_serial = '12345'
    gftv = gfibertv.GFiberTv(mailbox_url=mailbox_url, my_serial=my_serial)
    idx, newobj = gftv.AddExportObject('DeviceProperties', None)
    idx = int(idx)
    self.assertEqual(newobj, gftv.DevicePropertiesList[idx])
    self.assertEqual(None, gftv.DevicePropertiesList[idx].NickName)

    my_nickname = u'\u212ced\nroom\n\r!'
    gftv.DevicePropertiesList[idx].NickName = my_nickname
    gftv.DevicePropertiesList[idx].SerialNumber = '12345'

    self.loop.RunOnce()

    mynickfile = open(gfibertv.MYNICKFILE[0]).read()
    self.assertEqual(mynickfile, my_nickname.encode('utf-8'))

  def testBtFiles(self):
    gftv = gfibertv.GFiberTv('http://localhost:%d' % srv_port)
    self.loop.RunOnce()

    open(self.btdevices_fname, 'w').write('')
    open(self.bthhdevices_fname, 'w').write('')
    open(self.btconfig_fname, 'w').write('')

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

  def testTcpAlgorithm(self):
    open(self.tcpalgorithm_fname, 'w').write('westwood')
    gftv = gfibertv.GFiberTv('http://localhost:%d' % srv_port)
    self.assertEqual(gftv.TcpAlgorithm, 'westwood')
    gftv.TcpAlgorithm = ''
    self.loop.RunOnce()
    self.assertFalse(os.path.exists(self.tcpalgorithm_fname))
    gftv.TcpAlgorithm = 'foo'
    self.loop.RunOnce()
    self.assertEqual(open(self.tcpalgorithm_fname).read(), 'foo\n')

  def testOreganoFile(self):
    open(self.uicontrol_fname, 'w').write('http://uicontrol\n')
    gftv = gfibertv.GFiberTv('http://localhost:%d' % srv_port)
    self.assertEqual(gftv.UiControlUrl, 'http://uicontrol')
    gftv.UiControlUrl = 'http://cilantro'
    self.loop.RunOnce()
    self.assertEqual(open(self.uicontrol_fname).read(), 'http://cilantro\n')

  def testTvBuffer(self):
    open(self.tvbufferadddress_fname, 'w').write('1.2.3.4:1337\n')
    open(self.tvbufferkey_fname, 'w').write('monkeys\n')
    gftv = gfibertv.GFiberTv('http://localhost:%d' % srv_port)
    self.assertEqual(gftv.TvBufferAddress, '1.2.3.4:1337')
    self.assertEqual(gftv.TvBufferKey, 'monkeys')
    gftv.TvBufferAddress = '4.3.2.1:6666'
    gftv.TvBufferKey = 'monkeysaurus rex'
    self.loop.RunOnce()
    self.assertEqual(open(self.tvbufferadddress_fname).read(), '4.3.2.1:6666\n')
    self.assertEqual(open(self.tvbufferkey_fname).read(), 'monkeysaurus rex\n')

  def testHnvram(self):
    gfibertv.HNVRAM[0] = 'testdata/gfibertv/hnvram_read'
    gftv = gfibertv.GFiberTv('http://localhost:%d' % srv_port)
    self.assertEqual('ThisIsTheUiType', gftv.UiType)
    path = os.path.join(self.tmpdir, 'hnvram')
    gfibertv.HNVRAM = ['testdata/gfibertv/hnvram_write', path]
    self.assertFalse(os.path.exists(self.uitype_fname))
    gftv.UiType = 'SomeRandomUI'
    self.loop.RunOnce()
    self.assertEqual('SomeRandomUI', open(self.uitype_fname).read())
    self.assertEqual('-w UITYPE=SomeRandomUI', open(path).read())

  def testHnvramFails(self):
    gfibertv.HNVRAM[0] = '/nosuchfile'
    gftv = gfibertv.GFiberTv('http://localhost:%d' % srv_port)
    self.assertRaises(OSError, lambda: setattr(gftv, 'UiType', 'foo'))
    gfibertv.HNVRAM[0] = 'testdata/gfibertv/hnvram_error'
    self.assertRaises(OSError, lambda: setattr(gftv, 'UiType', 'foo'))


if __name__ == '__main__':
  unittest.main()
