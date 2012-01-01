#!/usr/bin/python
# Copyright 2011 Google Inc. All Rights Reserved.
#
"""External API for TR-069 support.

The classes here represent the ACS (Auto Configuration Server) and CPE
(Customer Premises Equipment) endpoints in the TR-069 standard API.  You can
hand them an hierarchy of tr.core.Exporter and use the
TR-069 access methods to manipulate it.

This file doesn't implement the XML (SOAP-like) wrapper around the TR-069
API calls; it's just a python version of the API.
"""

__author__ = 'apenwarr@google.com (Avery Pennarun)'

import tornadi_fix       #pylint: disable-msg=W0611
import download


class TR069Service(object):
  """Represents a TR-069 SOAP RPC service."""

  def __init__(self):
    pass

  def GetRPCMethods(self):
    """Return a list of callable methods."""
    methods = []
    for i in sorted(dir(self)):
      if i[0].isupper():
        methods.append(i)
    return methods


class ACS(TR069Service):
  """Represents a TR-069 ACS (Auto Configuration Server)."""

  def __init__(self):
    TR069Service.__init__(self)
    self.cpe = None

  def Inform(self, cpe, root, events, max_envelopes,
             current_time, retry_count, parameter_list):
    """Called when the CPE first connects to the ACS."""
    print 'ACS.Inform'
    self.cpe = cpe

  def TransferComplete(self, command_key, fault_struct,
                       start_time, complete_time):
    """A file transfer requested by the ACS has been completed."""
    raise NotImplementedError()

  def AutonomousTransferComplete(self,
                                 announce_url, transfer_url,
                                 is_download, file_type,
                                 file_size, target_filename, fault_struct,
                                 start_time, complete_time):
    """A file transfer *not* requested by the ACS has been completed."""
    raise NotImplementedError()

  def Kicked(self, command, referer, arg, next_url):
    """Called whenever the CPE is kicked by the ACS."""
    raise NotImplementedError()

  def RequestDownload(self, file_type, file_type_args):
    """The CPE wants us to tell it to download something."""
    raise NotImplementedError()

  def DUStateChangeComplete(self, results, command_key):
    """A requested ChangeDUState has completed."""
    raise NotImplementedError()

  def AutonomousDUStateChangeComplete(self, results):
    """A DU state change that was not requested by the ACS has completed."""
    raise NotImplementedError()


class CPE(TR069Service):
  """Represents a TR-069 CPE (Customer Premises Equipment)."""

  def __init__(self, root):
    TR069Service.__init__(self)
    self._last_parameter_key = None
    self.root = root
    self.download_manager = download.DownloadManager()

  def SetDownloadCalls(self, send_transfer_complete):
    self.download_manager.SEND_TRANSFER_COMPLETE = send_transfer_complete

  def _SetParameterKey(self, value):
    self._last_parameter_key = value

  def _SplitParameterName(self, name):
    """Split a name like Top.Object.1.Name into (Top.Object.1, Name)."""
    result = name.rsplit('.', 1)
    if len(result) == 2:
      return result[0], result[1]
    elif len(result) == 1:
      return None, result[0]
    elif not result:
      return None
    else:
      assert False

  def _SetParameterValue(self, name, value):
    """Given a parameter (which can include an object), set its value."""
    if name == 'ParameterKey':
      self._SetParameterKey(value)
    else:
      self.root.SetExportParam(name, value)

  def SetParameterValues(self, parameter_list, parameter_key):
    """Sets parameters on some objects."""
    # TODO(apenwarr): implement *atomic* setting of multiple values
    # TODO(apenwarr): implement correct handling of invalid parameter names
    for name, value in parameter_list:
      self._SetParameterValue(name, value)
    self._SetParameterKey(parameter_key)
    return 0  # all values changed successfully

  def _GetParameterValue(self, name):
    """Given a parameter (which can include an object), return its value."""
    if name == 'ParameterKey':
      return self._last_parameter_key
    else:
      return self.root.GetExport(name)

  def GetParameterValues(self, parameter_names):
    """Gets parameters from some objects.

    Args:
      parameter_names: a list of parameter name strings.
    Returns:
      A list of (name, value) tuples.
    """
    result = []
    for i in parameter_names:
      result.append((i, self._GetParameterValue(i)))
    return result

  def GetParameterNames(self, parameter_path, next_level_only):
    """Get the names of parameters or objects (possibly recursively)."""
    return self.root.ListExports(parameter_path, not next_level_only)

  def SetParameterAttributes(self, parameter_list):
    """Set attributes (access control, notifications) on some parameters."""
    raise NotImplementedError()

  def GetParameterAttributes(self, parameter_names):
    """Get attributes (access control, notifications) on some parameters."""
    raise NotImplementedError()

  def AddObject(self, object_name, parameter_key):
    """Create a new object with default parameters."""
    assert object_name.endswith('.')
    #pylint: disable-msg=W0612
    (idx, obj) = self.root.AddExportObject(object_name[:-1])
    self._SetParameterKey(parameter_key)
    return (idx, 0)  # successfully created

  def DeleteObject(self, object_name, parameter_key):
    """Delete an object and its sub-objects/parameters."""
    path = object_name.split('.')
    self.root.DeleteExportObject('.'.join(path[:-1]), path[-1])
    self._SetParameterKey(parameter_key)
    return 0  # successfully deleted

  def Download(self, command_key, file_type, url,
               username, password, file_size, target_filename,
               delay_seconds, success_url, failure_url):
    """Initiate a download immediately or after a delay."""
    return self.download_manager.NewDownload(
        command_key=command_key,
        file_type=file_type,
        url=url,
        username=username,
        password=password,
        file_size=file_size,
        target_filename=target_filename,
        delay_seconds=delay_seconds)

  def Reboot(self, command_key):
    """Reboot the CPE."""
    raise NotImplementedError()

  def GetQueuedTransfers(self):
    """Retrieve a list of queued file transfers (downloads and uploads)."""
    return self.download_manager.GetAllQueuedTransfers()

  def ScheduleInform(self, delay_seconds, command_key):
    """Request that this CPE call Inform() at some point in the future."""
    raise NotImplementedError()

  def SetVouchers(self, voucher_list):
    """Set option vouchers (deprecated)."""
    raise NotImplementedError()

  def GetOptions(self, option_name):
    """Get option vouchers (deprecated)."""
    raise NotImplementedError()

  def Upload(self, command_key, file_type, url,
             username, password, delay_seconds):
    """Initiate a file upload immediately or after a delay."""
    raise NotImplementedError()

  def FactoryReset(self):
    """Factory reset the CPE."""
    raise NotImplementedError()

  def GetAllQueuedTransfers(self):
    """Get a list of all uploads/downloads that are still in the queue."""
    return self.download_manager.GetAllQueuedTransfers()

  def ScheduleDownload(self, command_key, file_type, url,
                       username, password, file_size, target_filename,
                       time_window_list):
    """Schedule a download for some time in the future."""
    raise NotImplementedError()

  def CancelTransfer(self, command_key):
    """Cancel a scheduled file transfer."""
    return self.download_manager.CancelTransfer(command_key)

  def ChangeDUState(self, operations, command_key):
    """Trigger an install, update, or uninstall operation."""
    raise NotImplementedError()

  def TransferCompleteResponseReceived(self):
    return self.download_manager.TransferCompleteResponseReceived()
