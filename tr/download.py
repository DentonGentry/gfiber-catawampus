#!/usr/bin/python
# Copyright 2011 Google Inc. All Rights Reserved.
#
"""Handlers for tr-69 Download and Scheduled Download"""

__author__ = 'dgentry@google.com (Denton Gentry)'

import collections
import errno
import glob
import hashlib
import http_download
import json
import os
import persistobj
import random
import sys
import tempfile
import time
import tornadi_fix
import tornado
import tornado.httpclient
import tornado.ioloop
import tornado.web
import urlparse

# Persistent object storage location and filename
STATEDIR = "/tmp"
ROOTNAME = "tr69_dnld"

# tr-69 fault codes
INTERNAL_ERROR = 9002
INVALID_ARGUMENTS = 9003
RESOURCES_EXCEEDED = 9004


def SetStateDir(dir):
  global STATEDIR
  try:
    os.makedirs(dir, 0755)
  except OSError, e:
    if e.errno == errno.EEXIST:
      pass
    else:
      raise
  STATEDIR = dir


class Installer(object):
  """Install a downloaded image and reboot.

  This default implementation returns an error response. Platforms are
  expected to implement their own Install object, and set
  tr.download.INSTALLER = their object.
  """
  def __init__(self, filename):
    self.filename = filename

  def install(self, file_type, target_filename, callback):
    self.callback(faultcode=INTERNAL_ERROR,
                  faultstring='No installer for this platform.',
                  must_reboot=False)

  def reboot(self):
    return False

# Class to be called after image is downloaded. Platform code is expected
# to put its own installer here, the default returns failed to install.
INSTALLER = Installer


class SchemeFaultDownload(object):
  """A fake Download class used for bad URL schemes.

  If we get a URL schemewe don't implement, like foo://bar/,
  we need to signal an error back to the ACS. This class responds
  to any fetch() with an error.
  """
  def __init__(self, url, username=None, password=None,
               download_complete_cb=None, ioloop=None):
    self.url = url
    self.download_complete_cb = download_complete_cb

  def fetch(self):
    o = urlparse.urlparse(url)
    scheme = o.scheme if o.scheme else '<invalidURL>'
    self.download_complete_cb(INTERNAL_ERROR,
                              "Unsupported URL scheme {0}".format(scheme))


# Unit tests can substitute mock objects here
DOWNLOAD_CLIENT = {
  'http' : http_download.HttpDownload,
  'https' : http_download.HttpDownload
}


# State machine description. Generate a diagram using Graphviz:
# ./download.py
graphviz = r"""
digraph DLstates {
  node [shape=box]

  START [label="START"]
  WAITING [label="WAITING\nstart timer"]
  DOWNLOADING [label="DOWNLOADING\nstart download"]
  INSTALLING [label="INSTALLING\nstart install"]
  REBOOTING [label="REBOOTING\ninitiate reboot"]
  EXITING [label="EXITING\nsend TransferComplete"]
  DONE [label="DONE\ncleanup, not a\nreal state"]

  START -> WAITING
  START -> EXITING [label="invalid\ndownload"]
  WAITING -> DOWNLOADING [label="timer\nexpired"]
  DOWNLOADING -> INSTALLING [label="download\ncomplete"]
  DOWNLOADING -> EXITING [label="download\nfailed"]
  INSTALLING -> REBOOTING [label="install\ncomplete"]
  INSTALLING -> EXITING [label="install\nfailed"]
  INSTALLING -> EXITING [label="must_reboot=False"]
  REBOOTING -> EXITING [label="rebooted,\ncorrect image"]
  REBOOTING -> EXITING [label="rebooted,\nincorrect image"]
  EXITING -> DONE [label="receive\nTransferCompleteResponse"]
}
"""

class Download(object):
  """A state machine to handle a single tr-69 Download RPC."""

  # States in the state machine. See docs/download.dot for details
  START = "START"
  WAITING = "WAITING"
  DOWNLOADING = "DOWNLOADING"
  INSTALLING = "INSTALLING"
  REBOOTING = "REBOOTING"
  EXITING = "EXITING"

  # State machine events
  EV_START = 1
  EV_TIMER = 2
  EV_DOWNLOAD_COMPLETE = 3
  EV_INSTALL_COMPLETE = 4
  EV_REBOOT_COMPLETE = 5
  EV_TCRESPONSE = 6
  EV_IMMED_COMPLETE = 7

  def __init__(self, stateobj, transfer_complete_cb, ioloop=None):
    """Download object.

    Args:
      stateobj - a PersistentObject to store state across reboots.
        This class requires that command_key and url attributes be present.
      transfer_complete_cb - function to send a TransferComplete message.
      ioloop - Tornado ioloop. Unit tests can pass in a mock.
    """
    self.stateobj = self._restore_dlstate(stateobj)
    self.transfer_complete_cb = transfer_complete_cb
    self.ioloop = ioloop or tornado.ioloop.IOLoop.instance()
    self.downloaded_file = None
    # the delay_seconds started when we received the RPC, even if we have
    # downloaded other files and rebooted since then.
    if not hasattr(self.stateobj, 'wait_start_time'):
      self.stateobj.Update(wait_start_time=time.time())

  def _restore_dlstate(self, stateobj):
    """Re-enter the state machine at a sane state.

    This state machine is supposed to download a file, install that file,
    reboot, and send a completion. To do this it stores its state to
    the filesystem so it can read it back in after a reboot.

    If we reboot unexpectedly, like a power failure, we may have to backtrack.
    For example if we had downloaded the file to /tmp and then powered off,
    we lose the file and have to download it again.

    The state machine can only resume into the START and REBOOTING states.
    """
    if not hasattr(stateobj, 'dlstate'):
      stateobj.Update(dlstate=self.START)
    dlstate = stateobj.dlstate
    if dlstate != self.START and dlstate != self.REBOOTING:
      stateobj.Update(dlstate=self.START)
    return stateobj

  def _schedule_timer(self):
    delay_seconds = getattr(self.stateobj, 'delay_seconds', 0)
    wait_start_time = self.stateobj.wait_start_time

    # sanity check. If wait_start_time is in the future, ignore it.
    now = time.time()
    if wait_start_time > now:
      wait_start_time = now

    # I dislike when APIs require NTP-related bugs in my code.
    self.ioloop.add_timeout(wait_start_time + delay_seconds,
                            self.timer_callback)

  def _new_download_object(self, stateobj):
    url = getattr(stateobj, 'url', '')
    username = getattr(stateobj, 'username', None)
    password = getattr(stateobj, 'password', None)
    o = urlparse.urlparse(url)
    client = DOWNLOAD_CLIENT.get(o.scheme, SchemeFaultDownload)
    return client(url=url, username=username, password=password,
                  download_complete_cb=self.download_complete_callback)

  def _send_transfer_complete(self, faultcode, faultstring, start=0.0, end=0.0):
    self.transfer_complete_cb(command_key=self.stateobj.command_key,
                              faultcode=faultcode,
                              faultstring=faultstring,
                              starttime=start, endtime=end)

  def _remove_file(self, filename):
    try:
      os.unlink(filename)
    except OSError:
      return False
    return True

  def state_machine(self, event, faultcode=0, faultstring='',
                    downloaded_file=None, must_reboot=False):
    dlstate = self.stateobj.dlstate
    if dlstate == self.START:
      if event == self.EV_START or event == self.EV_REBOOT_COMPLETE:
        self.stateobj.Update(dlstate=self.WAITING)
        self._schedule_timer()
      elif event == self.EV_IMMED_COMPLETE:
        self.stateobj.Update(dlstate=self.EXITING)
        self._send_transfer_complete(faultcode, faultstring)

    elif dlstate == self.WAITING:
      if event == self.EV_TIMER:
        self.download = self._new_download_object(self.stateobj)
        self.stateobj.Update(dlstate=self.DOWNLOADING,
                             download_start_time=time.time())
        self.download.fetch()

    elif dlstate == self.DOWNLOADING:
      if event == self.EV_DOWNLOAD_COMPLETE:
        self.download = None  # no longer needed
        if faultcode == 0:
          self.installer = INSTALLER(downloaded_file)
          self.stateobj.Update(dlstate=self.INSTALLING)
          file_type = getattr(self.stateobj, 'file_type', None)
          target_filename = getattr(self.stateobj, 'target_filename', None)
          self.installer.install(file_type=file_type,
                                 target_filename=target_filename,
                                 callback=self.installer_callback)
        else:
          self.stateobj.Update(dlstate=self.EXITING)
          self._send_transfer_complete(faultcode, faultstring)

    elif dlstate == self.INSTALLING:
      if event == self.EV_INSTALL_COMPLETE:
        self._remove_file(self.downloaded_file)
        if faultcode == 0:
          if must_reboot:
            self.stateobj.Update(dlstate=self.REBOOTING)
            self.installer.reboot()
          else:
            end = time.time()
            self.stateobj.Update(dlstate=self.EXITING,
                                 download_complete_time=end)
            start = getattr(self.stateobj, 'download_start_time', 0.0)
            self._send_transfer_complete(faultcode=0, faultstring='',
                                         start=start, end=end)
        else:
          self.stateobj.Update(dlstate=self.EXITING)
          self._send_transfer_complete(faultcode, faultstring)

    elif dlstate == self.REBOOTING:
      if event == self.EV_REBOOT_COMPLETE:
        # TODO(dgentry) check version, whether image was actually installed
        end = time.time()
        self.stateobj.Update(dlstate=self.EXITING, download_complete_time=end)
        if faultcode == 0:
          start = getattr(self.stateobj, 'download_start_time', 0.0)
          self._send_transfer_complete(faultcode=0, faultstring='',
                                       start=start, end=end)
        else:
          self._send_transfer_complete(faultcode, faultstring)

    elif dlstate == self.EXITING:
      if event == self.EV_TCRESPONSE:
        self.stateobj.Delete()
        return True

  def do_start(self):
    return self.state_machine(self.EV_START)

  def do_immediate_complete(self, faultcode, faultstring):
    return self.state_machine(self.EV_IMMED_COMPLETE, faultcode, faultstring)

  def timer_callback(self):
    """Called by timer code when timeout expires."""
    return self.state_machine(self.EV_TIMER)

  def download_complete_callback(self, faultcode, faultstring, filename):
    self.downloaded_file = filename
    return self.state_machine(self.EV_DOWNLOAD_COMPLETE, faultcode, faultstring,
                              downloaded_file=filename)

  def installer_callback(self, faultcode, faultstring, must_reboot):
    return self.state_machine(self.EV_INSTALL_COMPLETE, faultcode, faultstring,
                              must_reboot=must_reboot)

  def reboot_callback(self, faultcode, faultstring):
    return self.state_machine(self.EV_REBOOT_COMPLETE, faultcode, faultstring)

  def transfer_complete_response(self):
    return self.state_machine(self.EV_TCRESPONSE, 0, None)

  def get_queue_state(self):
    """Data needed for GetQueuedTransfers/GetAllQueuedTransfers RPC."""
    q = collections.namedtuple('queued_transfer_struct',
        ('CommandKey State IsDownload FileType FileSize TargetFileName'))
    q.CommandKey = self.stateobj.command_key

    dlstate = self.stateobj.dlstate
    if dlstate == self.START or dlstate == self.WAITING:
      qstate = 1  # Not yet started
    elif dlstate == self.EXITING:
      qstate = 3  # Completed, finishing cleanup
    else:
      qstate = 2  # In progress
    q.State = qstate

    q.IsDownload = True
    q.FileType = getattr(self.stateobj, 'file_type', None)
    q.FileSize = getattr(self.stateobj, 'file_size', 0)
    q.TargetFileName = getattr(self.stateobj, 'target_filename', '')
    return q


class DownloadManager(object):
  """Manage Download requests from the ACS.

  Each RPC gets a Download object, which runs a state machine to track
  the progress of the operation. The DownloadManager allocates, manages
  and deletes the active Download objects.

  SPEC: http://www.broadband-forum.org/technical/download/TR-069_Amendment-3.pdf
  """

  # Maximum simultaneous downloads. tr-69 requires minimum of 3.
  MAXDOWNLOADS = 3

  # Object to track an individual Download RPC. Unit tests can override this.
  DOWNLOADOBJ = Download

  # Functions to send RPCs, to be filled in by parent object.
  SEND_DOWNLOAD_RESPONSE = None
  SEND_TRANSFER_COMPLETE = None

  def __init__(self):
    self._downloads = dict()

  def NewDownload(self, command_key=None, file_type=None, url=None,
                  username=None, password=None, file_size=0,
                  target_filename=None, delay_seconds=0):
    """Initiate a new download, handling a tr-69 Download RPC.

    Args:
      command_key, file_type, url, username, password, file_size,
      target_filename, delay_seconds - as defined in tr-69 Amendment 3
      (page 82 of $SPEC)

    Returns:
    (status, starttime, endtime) where
    status: numeric response code for the DownloadResponse.Status
    starttime: a float number of seconds, for the DownloadResponse.StartTime
    endtime: a float number of seconds, for the DownloadResponse.CompleteTime
    """

    # status=1 == send TransferComplete later, $SPEC pg 85
    self.SEND_DOWNLOAD_RESPONSE(1, 0.0, 0.0)

    # TODO(dgentry) check free space?

    faultcode = 0

    if command_key in self._downloads:
      # The ACS sends the same Download RPC several times. It likely has
      # some state that a CPE needs to be updated, and sends a Download
      # in response to every action we take.
      # Acknowledge it, but download only once and send one TransferComplete.
      return

    if len(self._downloads) >= self.MAXDOWNLOADS:
      faultcode = RESOURCES_EXCEEDED
      faultstring = "Max downloads ({0}) reached.".format(self.MAXDOWNLOADS)

    o = urlparse.urlparse(url)
    if o.scheme not in DOWNLOAD_CLIENT:
      faultcode = INVALID_ARGUMENTS
      faultstring = "Unsupported URL scheme {0}".format(o.scheme)

    kwargs = dict(command_key=command_key,
                  file_type=file_type,
                  url=url,
                  username=username,
                  password=password,
                  file_size=file_size,
                  target_filename=target_filename,
                  delay_seconds=delay_seconds)
    pobj = persistobj.PersistentObject(dir=STATEDIR, rootname=ROOTNAME,
                                       filename=None, **kwargs)
    dl = self.DOWNLOADOBJ(stateobj=pobj,
                          transfer_complete_cb=self.SEND_TRANSFER_COMPLETE)
    self._downloads[command_key] = dl

    if faultcode == 0:
      dl.do_start()
    else:
      dl.do_immediate_complete(faultcode, faultstring)

  def RestoreDownloads(self):
    pobjs = persistobj.GetPersistentObjects(dir=STATEDIR, rootname=ROOTNAME)
    for pobj in pobjs:
      # Can't even signal a fault via TransferComplete without cmdkey
      if hasattr(pobj, "command_key"):
        dl = self.DOWNLOADOBJ(stateobj=pobj,
                              transfer_complete_cb=self.SEND_TRANSFER_COMPLETE)
        self._downloads[pobj.command_key] = dl
        dl.reboot_callback(0, None)

  def TransferCompleteResponseReceived(self, command_key):
    if command_key in self._downloads:
      dl = self._downloads[command_key]
      if dl.transfer_complete_response():
        del self._downloads[command_key]

  def GetAllQueuedTransfers(self):
    transfers = list()
    for dl in self._downloads.values():
      transfers.append(dl.get_queue_state())
    return transfers


def main():
  # Generate diagram for Download state machine
  import subprocess
  cmd = ["dot", "-Tpdf", "-odownloadStateMachine.pdf"]
  p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
  print p.communicate(input=graphviz)[0]

if __name__ == '__main__':
  main()
