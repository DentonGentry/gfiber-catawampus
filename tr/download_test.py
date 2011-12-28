#!/usr/bin/python
#
# Copyright 2011 Google Inc. All Rights Reserved.
#
# unittest requires method names starting in 'test'
#pylint: disable-msg=C6409

"""Unit tests for download.py"""

__author__ = 'dgentry@google.com (Denton Gentry)'

from collections import namedtuple
import download
import os
import shutil
import persistobj
import tempfile
import time
import tornado.ioloop
import unittest


mock_http_clients = []
class MockHttpClient(object):
  def __init__(self, io_loop=None):
    self.did_fetch = False
    self.request = None
    self.callback = None
    mock_http_clients.append(self)

  def fetch(self, request, callback):
    self.did_fetch = True
    self.request = request
    self.callback = callback


class MockIoloop(object):
  def __init__(self):
    self.time = None
    self.callback = None

  def add_timeout(self, time, callback):
    self.time = time
    self.callback = callback


mock_http_downloads = []
class MockHttpDownload(object):
  def __init__(self, url, username=None, password=None,
               download_complete_cb=None, ioloop=None):
    self.url = url
    self.username = username
    self.password = password
    self.download_complete_cb = download_complete_cb
    self.ioloop = ioloop
    self.did_fetch = False
    mock_http_downloads.append(self)

  def fetch(self):
    self.did_fetch = True


mock_installers = []
class MockInstaller(object):
  def __init__(self, filename):
    self.filename = filename
    self.did_install = False
    self.did_reboot = False
    self.file_type = None
    self.targe_filename = None
    self.install_callback = None
    mock_installers.append(self)

  def install(self, file_type, target_filename, callback):
    self.did_install = True
    self.file_type = file_type
    self.target_filename = target_filename
    self.install_callback = callback
    return True

  def reboot(self):
    self.did_reboot = True


class MockTransferComplete(object):
  def __init__(self):
    self.transfer_complete_called = False
    self.command_key = None
    self.faultcode = None
    self.faultstring = None
    self.starttime = None
    self.endtime = None

  def SendTransferComplete(self, command_key, faultcode, faultstring,
                           starttime, endtime):
    self.transfer_complete_called = True
    self.command_key = command_key
    self.faultcode = faultcode
    self.faultstring = faultstring
    self.starttime = starttime
    self.endtime = endtime


class DownloadTest(unittest.TestCase):
  def setUp(self):
    self.tmpdir = tempfile.mkdtemp()
    download.INSTALLER = MockInstaller
    self.done_command_key = None
    self.old_time = time.time
    del mock_installers[:]
    del mock_http_downloads[:]
    download.DOWNLOAD_CLIENT['http'] = MockHttpDownload
    download.DOWNLOAD_CLIENT['https'] = MockHttpDownload

  def tearDown(self):
    time.time = self.old_time
    shutil.rmtree(self.tmpdir)
    del mock_installers[:]
    del mock_http_clients[:]

  def mockTime(self):
    return 123456.0

  def QCheckBoring(self, dl, args):
    """Check get_queue_state() fields which don't change, and return qstate."""
    q = dl.get_queue_state()
    self.assertEqual(q.CommandKey, args["command_key"])
    self.assertTrue(q.IsDownload)
    self.assertEqual(q.FileType, args["file_type"])
    self.assertEqual(q.FileSize, args["file_size"])
    self.assertEqual(q.TargetFileName, args["target_filename"])
    return q.State

  def testSuccess(self):
    ioloop = MockIoloop()
    cmpl = MockTransferComplete()
    time.time = self.mockTime

    kwargs = dict(command_key="testCommandKey",
                  file_type="testFileType",
                  url="http://example.com/foo",
                  username="testUsername",
                  password="testPassword",
                  file_size=1000,
                  target_filename="testTargetFilename",
                  delay_seconds=99)
    stateobj = persistobj.PersistentObject(dir=self.tmpdir, rootname="testObj",
                                           filename=None, **kwargs)

    dl = download.Download(stateobj=stateobj,
                           transfer_complete_cb=cmpl.SendTransferComplete,
                           ioloop=ioloop)
    self.assertEqual(self.QCheckBoring(dl, kwargs), 1)  # 1: Not Yet Started

    # Step 1: Wait delay_seconds
    dl.do_start()
    self.assertEqual(ioloop.time, self.mockTime() + kwargs['delay_seconds'])
    self.assertEqual(self.QCheckBoring(dl, kwargs), 1)  # 1: Not Yet Started

    # Step 2: HTTP Download
    dl.timer_callback()
    self.assertEqual(len(mock_http_downloads), 1)
    http = mock_http_downloads[0]
    self.assertEqual(http.url, kwargs['url'])
    self.assertEqual(http.username, kwargs['username'])
    self.assertEqual(http.password, kwargs['password'])
    self.assertTrue(http.download_complete_cb)
    self.assertTrue(http.did_fetch)
    self.assertEqual(self.QCheckBoring(dl, kwargs), 2)  # 2: In process

    # Step 3: Install
    dlfile = '/path/to/downloaded/file'
    http.download_complete_cb(0, '', dlfile)
    self.assertEqual(len(mock_installers), 1)
    inst = mock_installers[0]
    self.assertTrue(inst.did_install)
    self.assertEqual(inst.file_type, kwargs['file_type'])
    self.assertEqual(inst.target_filename, kwargs['target_filename'])
    self.assertEqual(inst.filename, dlfile)
    self.assertFalse(inst.did_reboot)
    self.assertEqual(self.QCheckBoring(dl, kwargs), 2)  # 2: In process

    # Step 4: Reboot
    inst.install_callback(0, '', must_reboot=True)
    self.assertTrue(inst.did_reboot)
    self.assertEqual(self.QCheckBoring(dl, kwargs), 2)  # 2: In process

    # Step 5: Send Transfer Complete
    dl.reboot_callback(0, '')
    self.assertTrue(cmpl.transfer_complete_called)
    self.assertEqual(cmpl.command_key, kwargs['command_key'])
    self.assertEqual(cmpl.faultcode, 0)
    self.assertEqual(cmpl.faultstring, '')
    self.assertEqual(cmpl.starttime, self.mockTime())
    self.assertEqual(cmpl.endtime, self.mockTime())
    self.assertEqual(self.QCheckBoring(dl, kwargs), 3)  # 3: Cleaning up

    # Step 6: Wait for Transfer Complete Response
    self.assertTrue(dl.transfer_complete_response())
    self.assertEqual(self.QCheckBoring(dl, kwargs), 3)  # 3: Cleaning up

  def testImmediateComplete(self):
    ioloop = MockIoloop()
    cmpl = MockTransferComplete()
    time.time = self.mockTime

    kwargs = dict(command_key="testCommandKey",
                  url="http://example.com/foo",
                  delay_seconds=1)
    stateobj = persistobj.PersistentObject(dir=self.tmpdir, rootname="testObj",
                                           filename=None, **kwargs)

    dl = download.Download(stateobj=stateobj,
                           transfer_complete_cb=cmpl.SendTransferComplete,
                           ioloop=ioloop)

    # Step 1: Send TransferComplete
    dl.do_immediate_complete(418, 'TestImmediateComplete')
    self.assertTrue(cmpl.transfer_complete_called)
    self.assertEqual(cmpl.command_key, kwargs['command_key'])
    self.assertEqual(cmpl.faultcode, 418)
    self.assertEqual(cmpl.faultstring, 'TestImmediateComplete')
    self.assertEqual(cmpl.starttime, 0.0)
    self.assertEqual(cmpl.endtime, 0.0)

  def testDownloadFailed(self):
    ioloop = MockIoloop()
    cmpl = MockTransferComplete()
    time.time = self.mockTime

    kwargs = dict(command_key="testCommandKey",
                  url="http://example.com/foo",
                  delay_seconds=1)
    stateobj = persistobj.PersistentObject(dir=self.tmpdir, rootname="testObj",
                                           filename=None, **kwargs)

    dl = download.Download(stateobj=stateobj,
                           transfer_complete_cb=cmpl.SendTransferComplete,
                           ioloop=ioloop)

    # Step 1: Wait delay_seconds
    dl.do_start()
    self.assertEqual(ioloop.time, self.mockTime() + kwargs['delay_seconds'])

    # Step 2: HTTP Download
    dl.timer_callback()
    self.assertEqual(len(mock_http_downloads), 1)
    http = mock_http_downloads[0]
    self.assertEqual(http.url, kwargs['url'])

    # Step 3: Download fails
    http.download_complete_cb(100, 'TestDownloadError', None)
    self.assertEqual(len(mock_installers), 0)
    self.assertTrue(cmpl.transfer_complete_called)
    self.assertEqual(cmpl.command_key, kwargs['command_key'])
    self.assertEqual(cmpl.faultcode, 100)
    self.assertEqual(cmpl.faultstring, 'TestDownloadError')
    self.assertEqual(cmpl.starttime, 0.0)
    self.assertEqual(cmpl.endtime, 0.0)

  def testInstallFailed(self):
    ioloop = MockIoloop()
    cmpl = MockTransferComplete()
    time.time = self.mockTime

    kwargs = dict(command_key="testCommandKey",
                  url="http://example.com/foo",
                  delay_seconds=1)
    stateobj = persistobj.PersistentObject(dir=self.tmpdir, rootname="testObj",
                                           filename=None, **kwargs)

    dl = download.Download(stateobj=stateobj,
                           transfer_complete_cb=cmpl.SendTransferComplete,
                           ioloop=ioloop)

    # Step 1: Wait delay_seconds
    dl.do_start()
    self.assertEqual(ioloop.time, self.mockTime() + kwargs['delay_seconds'])

    # Step 2: HTTP Download
    dl.timer_callback()
    self.assertEqual(len(mock_http_downloads), 1)
    http = mock_http_downloads[0]
    self.assertEqual(http.url, kwargs['url'])

    # Step 3: Install
    dlfile = '/path/to/downloaded/file'
    http.download_complete_cb(0, '', dlfile)
    self.assertEqual(len(mock_installers), 1)
    inst = mock_installers[0]
    self.assertTrue(inst.did_install)
    self.assertEqual(inst.filename, dlfile)
    self.assertFalse(inst.did_reboot)

    # Step 4: Install Failed
    inst.install_callback(101, 'TestInstallError', must_reboot=False)
    self.assertTrue(cmpl.transfer_complete_called)
    self.assertEqual(cmpl.command_key, kwargs['command_key'])
    self.assertEqual(cmpl.faultcode, 101)
    self.assertEqual(cmpl.faultstring, 'TestInstallError')
    self.assertEqual(cmpl.starttime, 0.0)
    self.assertEqual(cmpl.endtime, 0.0)

  def testInstallNoReboot(self):
    ioloop = MockIoloop()
    cmpl = MockTransferComplete()
    time.time = self.mockTime

    kwargs = dict(command_key="testCommandKey",
                  url="http://example.com/foo",
                  delay_seconds=1)
    stateobj = persistobj.PersistentObject(dir=self.tmpdir, rootname="testObj",
                                           filename=None, **kwargs)

    dl = download.Download(stateobj=stateobj,
                           transfer_complete_cb=cmpl.SendTransferComplete,
                           ioloop=ioloop)

    # Step 1: Wait delay_seconds
    dl.do_start()
    self.assertEqual(ioloop.time, self.mockTime() + kwargs['delay_seconds'])

    # Step 2: HTTP Download
    dl.timer_callback()
    self.assertEqual(len(mock_http_downloads), 1)
    http = mock_http_downloads[0]
    self.assertEqual(http.url, kwargs['url'])

    # Step 3: Install
    dlfile = '/path/to/downloaded/file'
    http.download_complete_cb(0, '', dlfile)
    self.assertEqual(len(mock_installers), 1)
    inst = mock_installers[0]
    self.assertTrue(inst.did_install)
    self.assertEqual(inst.filename, dlfile)
    self.assertFalse(inst.did_reboot)

    # Step 4: Install Succeeded, no reboot
    inst.install_callback(0, '', must_reboot=False)
    self.assertTrue(cmpl.transfer_complete_called)
    self.assertEqual(cmpl.command_key, kwargs['command_key'])
    self.assertEqual(cmpl.faultcode, 0)
    self.assertEqual(cmpl.faultstring, '')
    self.assertEqual(cmpl.starttime, self.mockTime())
    self.assertEqual(cmpl.endtime, self.mockTime())


class MockDownloadResponse(object):
  def __init__(self):
    self.reset()

  def reset(self):
    self.status = None
    self.start = None
    self.end = None
    self.send_response_called = False

  def SendDownloadResponse(self, status, start, end):
    self.status = status
    self.start = start
    self.end = end
    self.send_response_called = True


mock_downloads = []
class MockDownloadObj(object):
  def __init__(self, stateobj, transfer_complete_cb, done_cb=None, ioloop=None):
    self.stateobj = stateobj
    self.transfer_complete_cb = transfer_complete_cb
    self.done_cb = done_cb
    self.ioloop = ioloop
    self.do_start_called = False
    self.immediate_complete_called = False
    self.faultcode = None
    self.faultstring = None
    self.reboot_callback_called = False
    mock_downloads.append(self)

  def do_start(self):
    self.do_start_called = True

  def do_immediate_complete(self, faultcode, faultstring):
    self.immediate_complete_called = True
    self.faultcode = faultcode
    self.faultstring = faultstring

  def reboot_callback(self, faultcode, faultstring):
    self.reboot_callback_called = True

  def get_queue_state(self):
    return "This_is_not_a_real_queue_state."


class DownloadManagerTest(unittest.TestCase):
  def setUp(self):
    self.tmpdir = tempfile.mkdtemp()
    self.old_statedir = download.STATEDIR
    download.STATEDIR = self.tmpdir
    del mock_downloads[:]

  def tearDown(self):
    download.STATEDIR = self.old_statedir
    shutil.rmtree(self.tmpdir)
    del mock_downloads[:]

  def allocTestDM(self):
    dm = download.DownloadManager()
    resp = MockDownloadResponse()
    cmpl = MockTransferComplete()
    dm.SEND_DOWNLOAD_RESPONSE = resp.SendDownloadResponse
    dm.SEND_TRANSFER_COMPLETE = cmpl.SendTransferComplete
    dm.DOWNLOADOBJ = MockDownloadObj
    return (dm, resp, cmpl)

  def testSimpleDownload(self):
    (dm, resp, cmpl) = self.allocTestDM()
    args = {"command_key": "TestCommandKey",
            "file_type": "TestFileType",
            "url": "http://example.com/",
            "username": "TestUser",
            "password": "TestPassword",
            "file_size": 99,
            "target_filename": "TestFilename",
            "delay_seconds": 30}
    dm.NewDownload(**args)
    self.assertTrue(resp.send_response_called)
    self.assertEqual(resp.status, 1)
    self.assertEqual(resp.start, 0.0)
    self.assertEqual(resp.end, 0.0)
    self.assertEqual(len(mock_downloads), 1)
    dl = mock_downloads[0]
    self.assertEqual(dl.stateobj.command_key, args["command_key"])
    self.assertEqual(dl.stateobj.file_type, args["file_type"])
    self.assertEqual(dl.stateobj.url, args["url"])
    self.assertEqual(dl.stateobj.username, args["username"])
    self.assertEqual(dl.stateobj.password, args["password"])
    self.assertEqual(dl.stateobj.file_size, args["file_size"])
    self.assertEqual(dl.stateobj.target_filename, args["target_filename"])
    self.assertEqual(dl.stateobj.delay_seconds, args["delay_seconds"])

  def testDuplicate(self):
    (dm, resp, cmpl) = self.allocTestDM()
    args = {"command_key": "TestCommandKey", "url": "http://example.com/"}
    dm.NewDownload(**args)
    self.assertTrue(resp.send_response_called)
    self.assertEqual(resp.status, 1)
    self.assertEqual(resp.start, 0.0)
    self.assertEqual(resp.end, 0.0)
    self.assertEqual(len(mock_downloads), 1)

    resp.reset()
    dm.NewDownload(**args)
    self.assertTrue(resp.send_response_called)
    self.assertEqual(resp.status, 1)
    self.assertEqual(resp.start, 0.0)
    self.assertEqual(resp.end, 0.0)
    # No new download created for the duplicate
    self.assertEqual(len(mock_downloads), 1)

  def testMaxDownloads(self):
    (dm, resp, cmpl) = self.allocTestDM()
    maxdl = download.DownloadManager.MAXDOWNLOADS + 1
    for i in range(maxdl):
      args = {"command_key": "TestCommandKey" + str(i),
              "url": "http://example.com/"}
      resp.reset()
      dm.NewDownload(**args)
      self.assertTrue(resp.send_response_called)
      self.assertEqual(resp.status, 1)
      self.assertEqual(resp.start, 0.0)
      self.assertEqual(resp.end, 0.0)
    self.assertEqual(len(mock_downloads), maxdl)
    dl = mock_downloads[maxdl-1]
    self.assertTrue(dl.immediate_complete_called)
    self.assertEqual(dl.faultcode, 9004)
    self.assertTrue(dl.faultstring)

  def testBadUrlScheme(self):
    (dm, resp, cmpl) = self.allocTestDM()
    args = {"command_key": "TestCommandKey",
            "url": "invalid://bad.url/"}
    dm.NewDownload(**args)
    self.assertTrue(resp.send_response_called)
    self.assertEqual(resp.status, 1)
    self.assertEqual(resp.start, 0.0)
    self.assertEqual(resp.end, 0.0)
    self.assertEqual(len(mock_downloads), 1)
    dl = mock_downloads[0]
    self.assertTrue(dl.immediate_complete_called)
    self.assertEqual(dl.faultcode, 9003)
    self.assertTrue(dl.faultstring)

  def testRestoreMultiple(self):
    (dm, resp, cmpl) = self.allocTestDM()
    numdl = 4
    for i in range(numdl):
      args = {"command_key": "TestCommandKey" + str(i),
              "file_type": "TestFileType",
              "url": "http://example.com/",
              "username": "TestUser",
              "password": "TestPassword",
              "file_size": 99,
              "target_filename": "TestFilename",
              "delay_seconds": 30}
      pobj = persistobj.PersistentObject(dir=download.STATEDIR,
                                         rootname=download.ROOTNAME,
                                         filename=None, **args)
    dm.RestoreDownloads()
    self.assertEqual(len(mock_downloads), numdl)
    for i in range(numdl):
      dl = mock_downloads[i]
      self.assertFalse(dl.do_start_called)
      self.assertFalse(dl.immediate_complete_called)
      self.assertTrue(dl.reboot_callback_called)

  def testGetAllQueuedTransfers(self):
    (dm, resp, cmpl) = self.allocTestDM()
    numdl = 2
    for i in range(numdl):
      args = {"command_key": "TestCommandKey" + str(i),
              "file_type": "TestFileType",
              "url": "http://example.com/",
              "username": "TestUser",
              "password": "TestPassword",
              "file_size": 99,
              "target_filename": "TestFilename",
              "delay_seconds": 30}
      dm.NewDownload(**args)
    transfers = dm.GetAllQueuedTransfers()
    self.assertEqual(len(transfers), numdl)


if __name__ == '__main__':
  unittest.main()
