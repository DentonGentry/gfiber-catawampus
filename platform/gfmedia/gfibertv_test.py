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
#pylint: disable-msg=C6409

"""Unit tests for tvxmlrpc.py."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import os
import SimpleXMLRPCServer
import tempfile
import threading
import unittest
import xmlrpclib
import google3
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
  """Tests for gfibertv.py and tvxmlrpc.py."""

  def setUp(self):
    srv_cv.acquire()
    self.server_thread = XmlRpcThread()
    self.server_thread.start()
    srv_cv.wait()
    (nick_file_handle, self.nick_file_name) = tempfile.mkstemp()
    (tmp_file_handle, self.tmp_file_name) = tempfile.mkstemp()
    os.close(nick_file_handle)
    os.close(tmp_file_handle)
    gfibertv.NICKFILE = self.nick_file_name
    gfibertv.NICKFILE_TMP = self.tmp_file_name

  def tearDown(self):
    xmlrpclib.ServerProxy('http://localhost:%d' % srv_port).Quit()
    self.server_thread.join()
    os.unlink(gfibertv.NICKFILE)

  def testValidate(self):
    tv = gfibertv.GFiberTv('http://localhost:%d' % srv_port)
    tv.Mailbox.Node = 'Node1'
    tv.Mailbox.Name = 'Prop1'
    tv.ValidateExports()

  def testGetProperties(self):
    tvrpc = gfibertv.GFiberTvMailbox('http://localhost:%d' % srv_port)
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
    tvrpc = gfibertv.GFiberTvMailbox('http://localhost:2')
    tvrpc.Node = 'Node1'
    tvrpc.Name = 'Prop1'
    self.assertRaises(IndexError, lambda: tvrpc.Value)

  def testSetProperties(self):
    tvrpc = gfibertv.GFiberTvMailbox('http://localhost:%d' % srv_port)
    tvrpc.Node = 'Node1'
    tvrpc.Name = 'Prop1'
    tvrpc.Value = 'Prop1NewValue'
    self.assertEqual(tvrpc.Value, 'Prop1NewValue')
    tvrpc.Name = 'Prop4'
    self.assertRaises(IndexError, lambda: tvrpc.Value)
    tvrpc.Node = 'Node3'
    self.assertRaises(IndexError, lambda: tvrpc.Value)

  def testSetPropertiesProtocolError(self):
    tvrpc = gfibertv.GFiberTvMailbox('http://localhost:2')
    tvrpc.Node = 'Node1'
    tvrpc.Name = 'Prop1'
    self.assertRaises(IndexError, lambda: tvrpc.SetValue(1))

  def testNodeList(self):
    tvrpc = gfibertv.GFiberTvMailbox('http://localhost:%d' % srv_port)
    self.assertEqual(tvrpc.NodeList, 'Node1, Node2')

  def testListManipulation(self):
    gftv = gfibertv.GFiberTv('http://localhost:1000')
    gftv.ValidateExports()
    self.assertEqual(0, gftv.DeviceNickNameNumberOfEntries)
    idx, newobj = gftv.AddExportObject('DeviceNickName', None)
    idx = int(idx)
    self.assertEqual(1, gftv.DeviceNickNameNumberOfEntries)
    self.assertEqual(newobj, gftv.DeviceNickNameList[idx])
    gftv.StartTransaction()
    gftv.DeviceNickNameList[idx].StartTransaction()
    gftv.DeviceNickNameList[idx].NickName = 'testroom'
    gftv.DeviceNickNameList[idx].SerialNumber = '12345'
    gftv.DeviceNickNameList[idx].AbandonTransaction()
    gftv.AbandonTransaction()
    self.assertEqual('', gftv.DeviceNickNameList[idx].NickName)

    gftv.StartTransaction()
    idx2, newobj = gftv.AddExportObject('DeviceNickName', None)
    idx2 = int(idx2)
    gftv.DeviceNickNameList[idx].StartTransaction()
    gftv.DeviceNickNameList[idx].NickName = 'testroom'
    gftv.DeviceNickNameList[idx].SerialNumber = '12345'
    gftv.DeviceNickNameList[idx].CommitTransaction()

    gftv.DeviceNickNameList[idx2].StartTransaction()
    uni_name = u'\u212ced\nroom\n\r!'.encode('utf-8')
    gftv.DeviceNickNameList[idx2].NickName = uni_name
    gftv.DeviceNickNameList[idx2].SerialNumber = '56789'
    gftv.DeviceNickNameList[idx2].CommitTransaction()

    gftv.CommitTransaction()

    # read the test file back in.
    f = file(gfibertv.NICKFILE, 'r')
    lines = set()
    lines.add(f.readline())
    lines.add(f.readline())
    last_line = f.readline()
    last_line = last_line.strip()

    self.assertTrue('12345/nickname=testroom\n' in lines)
    self.assertTrue('56789/nickname=\u212cedroom!\n' in lines)
    self.assertTrue(last_line.startswith('SERIALS='))
    split1 = last_line.split('=')
    self.assertEqual(2, len(split1))
    split2 = split1[1].split(',')
    self.assertTrue('12345' in split2)
    self.assertTrue('56789' in split2)
    f.close()


if __name__ == '__main__':
  unittest.main()
