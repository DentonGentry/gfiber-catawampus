#!/usr/bin/python
# Copyright 2011 Google Inc. All Rights Reserved.
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
#
# pylint:disable=unused-argument

"""Handlers for tr-69 Download and Scheduled Download."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import collections
import datetime
import os
import time
import urlparse
import google3
import tornado
import tornado.httpclient
import tornado.ioloop
import tornado.web
import core
import persistobj
import session


# Persistent object storage filename
DNLDROOTNAME = 'tr69_dnld'
BOOTROOTNAME = 'tr69_boot'
INTERNAL_ERROR = 9002


class Installer(object):
  """Install a downloaded image and reboot.

  This default implementation returns an error response. Platforms are
  expected to implement their own Install object, and set
  tr.download.INSTALLER = their object.
  """

  def Install(self, file_type, target_filename, callback):
    callback(faultcode=INTERNAL_ERROR,
             faultstring='No installer for this platform.',
             must_reboot=False)

  def Reboot(self):
    return False

# Class to be called after image is downloaded. Platform code is expected
# to put its own installer here, the default returns failed to install.
INSTALLER = Installer


# State machine description. Generate a diagram using Graphviz:
# ./download.py
graphviz = r"""
digraph DLstates {
  node [shape=box]

  START [label="START"]
  WAITING [label="WAITING\nstart timer"]
  INSTALLING [label="INSTALLING\nstart install"]
  REBOOTING [label="REBOOTING\ninitiate reboot"]
  EXITING [label="EXITING\nsend TransferComplete"]
  DONE [label="DONE\ncleanup, not a\nreal state"]

  START -> WAITING
  WAITING -> INSTALLING [label="timer\nexpired"]
  INSTALLING -> EXITING [label="download\nfailed"]
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
  START = 'START'
  WAITING = 'WAITING'
  INSTALLING = 'INSTALLING'
  REBOOTING = 'REBOOTING'
  EXITING = 'EXITING'

  # State machine events
  EV_START = 1
  EV_TIMER = 2
  EV_DOWNLOAD_COMPLETE = 3
  EV_INSTALL_COMPLETE = 4
  EV_REBOOT_COMPLETE = 5
  EV_TCRESPONSE = 6

  def __init__(self, stateobj, transfer_complete_cb,
               download_dir=None, ioloop=None):
    """Download object.

    Args:
      stateobj: a PersistentObject to store state across reboots.
        This class requires that command_key and url attributes be present.
      transfer_complete_cb: function to send a TransferComplete message.
      download_dir: directory to download to
      ioloop: Tornado ioloop. Unit tests can pass in a mock.
    """
    self.stateobj = self._RestoreDlstate(stateobj)
    self.transfer_complete_cb = transfer_complete_cb
    self.download_dir = download_dir
    self.ioloop = ioloop or tornado.ioloop.IOLoop.instance()
    self.wait_handle = None
    # the delay_seconds started when we received the RPC, even if we have
    # downloaded other files and rebooted since then.
    if not hasattr(self.stateobj, 'wait_start_time'):
      self.stateobj.Update(wait_start_time=time.time())

  def CommandKey(self):
    return getattr(self.stateobj, 'command_key', None)

  def _RestoreDlstate(self, stateobj):
    """Re-enter the state machine at a sane state.

    This state machine is supposed to download a file, install that file,
    reboot, and send a completion. To do this it stores its state to
    the filesystem so it can read it back in after a reboot.

    If we reboot unexpectedly, like a power failure, we may have to backtrack.
    For example if we had downloaded the file to /tmp and then powered off,
    we lose the file and have to download it again.

    The state machine can only resume into the START and REBOOTING states.

    Args:
      stateobj: the PersistentObject for this transfer
    Returns:
      the stateobj
    """

    if not hasattr(stateobj, 'dlstate'):
      stateobj.Update(dlstate=self.START)
    dlstate = stateobj.dlstate
    if dlstate == self.REBOOTING or dlstate == self.EXITING:
      stateobj.Update(dlstate=self.REBOOTING)
    else:
      stateobj.Update(dlstate=self.START)
    return stateobj

  def _ScheduleTimer(self):
    """Set up a timer to trigger the state machine at the right future time."""
    delay_seconds = getattr(self.stateobj, 'delay_seconds', 0)
    now = time.time()
    wait_start_time = self.stateobj.wait_start_time

    # sanity checks
    if wait_start_time > now:
      wait_start_time = now
    when = wait_start_time + delay_seconds
    if when < now:
      when = now

    self.wait_handle = self.ioloop.add_timeout(
        datetime.timedelta(seconds=when - now),
        self.TimerCallback)

  def _SendTransferComplete(self, faultcode, faultstring, start=0.0, end=0.0):
    event_code = getattr(self.stateobj, 'event_code', 'M Download')
    self.transfer_complete_cb(dl=self,
                              command_key=self.stateobj.command_key,
                              faultcode=faultcode,
                              faultstring=faultstring,
                              starttime=start, endtime=end,
                              event_code=event_code)

  def StateMachine(self, event, faultcode=0, faultstring='',
                   downloaded_file=None, must_reboot=False):
    dlstate = self.stateobj.dlstate
    if dlstate == self.START:
      if event == self.EV_START or event == self.EV_REBOOT_COMPLETE:
        self.stateobj.Update(dlstate=self.WAITING)
        self._ScheduleTimer()

    elif dlstate == self.WAITING:
      if event == self.EV_TIMER:
        self.stateobj.Update(dlstate=self.INSTALLING,
                             download_start_time=time.time())
        self.installer = INSTALLER(url=self.stateobj.url)
        file_type = getattr(self.stateobj, 'file_type', None)
        target_filename = getattr(self.stateobj, 'target_filename', None)
        self.installer.Install(file_type=file_type,
                               target_filename=target_filename,
                               callback=self.InstallerCallback)
        # It is up to installer.Install to either install the image, or
        # callback with an error in case of timeout or failure.

    elif dlstate == self.INSTALLING:
      if event == self.EV_INSTALL_COMPLETE:
        if faultcode == 0:
          if must_reboot:
            self.stateobj.Update(dlstate=self.REBOOTING)
            self.installer.Reboot()
          else:
            end = time.time()
            self.stateobj.Update(dlstate=self.EXITING,
                                 download_complete_time=end)
            start = getattr(self.stateobj, 'download_start_time', 0.0)
            self._SendTransferComplete(faultcode=0, faultstring='',
                                       start=start, end=end)
        else:
          self.stateobj.Update(dlstate=self.EXITING)
          self._SendTransferComplete(faultcode, faultstring)

    elif dlstate == self.REBOOTING:
      if event == self.EV_REBOOT_COMPLETE:
        end = time.time()
        self.stateobj.Update(dlstate=self.EXITING, download_complete_time=end)
        if faultcode == 0:
          start = getattr(self.stateobj, 'download_start_time', 0.0)
          self._SendTransferComplete(faultcode=0, faultstring='',
                                     start=start, end=end)
        else:
          self._SendTransferComplete(faultcode, faultstring)

    elif dlstate == self.EXITING:
      pass

  def DoStart(self):
    return self.StateMachine(self.EV_START)

  def TimerCallback(self):
    """Called by timer code when timeout expires."""
    return self.StateMachine(self.EV_TIMER)

  def DownloadCompleteCallback(self, faultcode, faultstring, tmpfile):
    print 'Download complete callback.'
    name = tmpfile and tmpfile.name or None
    return self.StateMachine(self.EV_DOWNLOAD_COMPLETE,
                             faultcode, faultstring,
                             downloaded_file=name)

  def InstallerCallback(self, faultcode, faultstring, must_reboot):
    return self.StateMachine(self.EV_INSTALL_COMPLETE, faultcode, faultstring,
                             must_reboot=must_reboot)

  def RebootCallback(self, faultcode, faultstring):
    return self.StateMachine(self.EV_REBOOT_COMPLETE, faultcode, faultstring)

  def Cleanup(self):
    """Attempt to stop all activity and clean up resources.

    Returns:
      False - successfully stopped and cleaned up
      string - the reason download cannot be safely cancelled right now.
    """
    dlstate = self.stateobj.dlstate
    if dlstate == self.INSTALLING:
      return 'Download is currently installing to flash'
    if dlstate == self.REBOOTING:
      return 'Download has been installed, awaiting reboot'
    if self.wait_handle:
      self.ioloop.remove_timeout(self.wait_handle)
      self.wait_handle = None
    self.stateobj.Delete()

  def GetQueueState(self):
    """Data needed for GetQueuedTransfers/GetAllQueuedTransfers RPC."""
    q = collections.namedtuple(
        'queued_transfer_struct',
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


# Object to track an individual Download RPC. Unit tests can override this.
DOWNLOADOBJ = Download


class DownloadManager(object):
  """Manage Download requests from the ACS.

  Each RPC gets a Download object, which runs a state machine to track
  the progress of the operation. The DownloadManager allocates, manages
  and deletes the active Download objects.

  SPEC: http://www.broadband-forum.org/technical/download/TR-069_Amendment-3.pdf
  """

  # Maximum simultaneous downloads. tr-69 requires minimum of 3.
  MAXDOWNLOADS = 1

  def __init__(self, ioloop=None):
    self.ioloop = ioloop or tornado.ioloop.IOLoop.instance()
    self._downloads = list()
    self._pending_complete = list()
    self.config_dir = '/tmp/'
    # Function to send RPCs, to be filled in by parent object.
    self.send_transfer_complete = None

  def NewDownload(self, command_key=None, file_type=None, url=None,
                  username=None, password=None, file_size=0,
                  target_filename=None, delay_seconds=0):
    """Initiate a new download, handling a tr-69 Download RPC.

    Args:
      command_key: as defined in tr-69 Amendment 3 (page 82 of $SPEC)
      file_type: as defined in tr-69 Amendment 3 (page 82 of $SPEC)
      url: as defined in tr-69 Amendment 3 (page 82 of $SPEC)
      username: as defined in tr-69 Amendment 3 (page 82 of $SPEC)
      password: as defined in tr-69 Amendment 3 (page 82 of $SPEC)
      file_size: as defined in tr-69 Amendment 3 (page 82 of $SPEC)
      target_filename: as defined in tr-69 Amendment 3 (page 82 of $SPEC)
      delay_seconds: as defined in tr-69 Amendment 3 (page 82 of $SPEC)

    Raises:
      core.ResourcesExceededError: too many simultaneous downloads
      core.FileTransferProtocolError: Unsupported URL type, ex: ftp

    Returns:
      (code, starttime, endtime):
      code = status to return (1 == send TransferComplete later, $SPEC pg 85)
      starttime, endtime = two floating point numbers in seconds for the
        StartTime and CompleteTime of the DownloadResponse.
    """

    if len(self._downloads) >= self.MAXDOWNLOADS:
      faultstring = 'Max downloads (%d) reached.' % self.MAXDOWNLOADS
      raise core.ResourcesExceededError(faultstring)

    o = urlparse.urlparse(url)
    if o.scheme not in ['http', 'https']:
      raise core.FileTransferProtocolError(
          'Unsupported URL scheme %s' % o.scheme)

    kwargs = dict(command_key=command_key,
                  file_type=file_type,
                  url=url,
                  username=username,
                  password=password,
                  file_size=file_size,
                  target_filename=target_filename,
                  delay_seconds=delay_seconds,
                  event_code='M Download')
    pobj = persistobj.PersistentObject(objdir=self.config_dir,
                                       rootname=DNLDROOTNAME,
                                       filename=None,
                                       ignore_errors=True,
                                       **kwargs)
    dl = DOWNLOADOBJ(stateobj=pobj,
                     transfer_complete_cb=self.TransferCompleteCallback)
    self._downloads.append(dl)
    dl.DoStart()

    return (1, 0.0, 0.0)

  def TransferCompleteCallback(self, dl, command_key, faultcode, faultstring,
                               starttime, endtime, event_code):
    self._downloads.remove(dl)
    self._pending_complete.append(dl)
    if self.send_transfer_complete:
      self.send_transfer_complete(  # pylint:disable=not-callable
          command_key, faultcode, faultstring,
          starttime, endtime, event_code)

  def RestoreDownloads(self):
    pobjs = persistobj.GetPersistentObjects(objdir=self.config_dir,
                                            rootname=DNLDROOTNAME)
    for pobj in pobjs:
      if not hasattr(pobj, 'command_key'):
        print 'Download Object %s has no command_key' % pobj.filename
        pobj.Delete()
        continue
      dl = DOWNLOADOBJ(stateobj=pobj,
                       transfer_complete_cb=self.TransferCompleteCallback)
      self._downloads.append(dl)
      dl.RebootCallback(0, None)

  def TransferCompleteResponseReceived(self):
    dl = self._pending_complete.pop()
    dl.Cleanup()

  def GetAllQueuedTransfers(self):
    transfers = list()
    for dl in self._downloads:
      transfers.append(dl.GetQueueState())
    for dl in self._pending_complete:
      transfers.append(dl.GetQueueState())
    return transfers

  def CancelTransfer(self, command_key):
    """Cancel an in-progress transfer.

    Args:
      command_key: the command_key to cancel. There can be multiple transfers
        with the same command_key. $SPEC says to attempt to cancel all of them,
        return failure if any cannot be cancelled.

    Raises:
      core.CancelNotPermitted: download cannot be cancelled right now.
    """
    for dl in self._downloads:
      if dl.CommandKey() == command_key:
        faultstring = dl.Cleanup()
        if faultstring:
          raise core.CancelNotPermitted(faultstring)
        else:
          self._downloads.remove(dl)
    for dl in self._pending_complete:
      if dl.CommandKey() == command_key:
        raise core.CancelNotPermitted(
            'Installed, awaiting TransferCompleteResponse')

  def _DelayedReboot(self):
    installer = INSTALLER('')
    installer.Reboot()

  def RestoreReboots(self):
    """Read state of Reboot RPCs in from storage."""
    pobjs = persistobj.GetPersistentObjects(objdir=self.config_dir,
                                            rootname=BOOTROOTNAME)
    reboots = []
    for pobj in pobjs:
      if hasattr(pobj, 'command_key'):
        reboots.append(('M Reboot', pobj.command_key))
      else:
        print 'Reboot object %s has no command_key' % pobj.filename
      pobj.Delete()
    return reboots

  def Reboot(self, command_key):
    """Reboot the system."""
    kwargs = dict(command_key=command_key)
    persistobj.PersistentObject(objdir=self.config_dir, rootname=BOOTROOTNAME,
                                filename=None, **kwargs)
    session.RunAtEnd(self._DelayedReboot)

  def _MakeDirsIgnoreError(self, directory):
    """Make sure a directory exists."""
    try:
      os.makedirs(directory, 0755)
    except OSError:
      pass

  def SetDirectories(self, config_dir, download_dir):
    self.config_dir = os.path.join(config_dir, 'state')
    self.download_dir = os.path.join(download_dir, 'dnld')
    self._MakeDirsIgnoreError(self.config_dir)
    self._MakeDirsIgnoreError(self.download_dir)


def main():
  # Generate diagram for Download state machine
  import subprocess  # pylint:disable=g-import-not-at-top
  cmd = ['dot', '-Tpdf', '-odownloadStateMachine.pdf']
  p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
  print p.communicate(input=graphviz)[0]

if __name__ == '__main__':
  main()
