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

import core


DEVICE_ID = 'google-test-device-id'

_last_parameter_key = None


def _SetParameterKey(value):
  global _last_parameter_key
  _last_parameter_key = value


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

  def Inform(self, cpe,
             device_id, events, max_envelopes,
             current_time, retry_count, parameter_list):
    """Called when the CPE first connects to the ACS."""
    pass

  def TransferComplete(self, cpe,
                       command_key, fault_struct,
                       start_time, complete_time):
    """A file transfer requested by the ACS has been completed."""
    raise NotImplementedError()

  def AutonomousTransferComplete(self, cpe,
                                 announce_url, transfer_url,
                                 is_download, file_type,
                                 file_size, target_filename, fault_struct,
                                 start_time, complete_time):
    """A file transfer *not* requested by the ACS has been completed."""
    raise NotImplementedError()

  def Kicked(self, cpe,
             command, referer, arg, next_url):
    """Called whenever the CPE is kicked by the ACS."""
    raise NotImplementedError()

  def RequestDownload(self, cpe,
                      file_type, file_type_args):
    """The CPE wants us to tell it to download something."""
    raise NotImplementedError()

  def DUStateChangeComplete(self, cpe,
                            results, command_key):
    """A requested ChangeDUState has completed."""
    raise NotImplementedError()

  def AutonomousDUStateChangeComplete(self, cpe,
                                      results):
    """A DU state change that was not requested by the ACS has completed."""
    raise NotImplementedError()


class CPE(TR069Service):
  """Represents a TR-069 CPE (Customer Premises Equipment)."""

  def __init__(self, acs, root):
    TR069Service.__init__(self)
    self.acs = acs
    self.root = root
    self.acs.Inform(self, DEVICE_ID,
                    events=[], max_envelopes=1,
                    current_time=None, retry_count=1,
                    parameter_list=[])

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
      _SetParameterKey(value)
    else:
      obj_name, param_name = self._SplitParameterName(name)
      self.root.GetExport(obj_name).SetExportParam(param_name, value)

  def SetParameterValues(self, parameter_list, parameter_key):
    """Sets parameters on some objects."""
    # TODO(apenwarr): implement *atomic* setting of multiple values
    # TODO(apenwarr): implement correct handling of invalid parameter names
    for name, value in parameter_list:
      self._SetParameterValue(name, value)
    _SetParameterKey(parameter_key)
    return 0  # all values changed successfully

  def _GetParameterValue(self, name):
    """Given a parameter (which can include an object), return its value."""
    if name == 'ParameterKey':
      return _last_parameter_key
    else:
      obj_name, param_name = self._SplitParameterName(name)
      return self.root.GetExport(obj_name).GetExport(param_name)

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
    # TODO(apenwarr): implement this *correctly* with recursion etc.
    # For now, we assume parameter_path just names an object.
    # And we ignore next_level_only.
    assert parameter_path.endswith('.')
    obj_name = parameter_path[:-1]
    base_names = self.root.GetExport(obj_name).ListExports()
    out = []
    for i in base_names:
      out.append('%s.%s' % (obj_name, i))
    return out

  def SetParameterAttributes(self, parameter_list):
    """Set attributes (access control, notifications) on some parameters."""
    raise NotImplementedError()

  def GetParameterAttributes(self, parameter_names):
    """Get attributes (access control, notifications) on some parameters."""
    raise NotImplementedError()

  def AddObject(self, object_name, parameter_key):
    """Create a new object with default parameters."""
    assert object_name.endswith('.')
    path = object_name.split('.')
    parent = self.root.GetExport('.'.join(path[:-2]))
    idx,obj = parent.AddExportObject(path[-2])
    _SetParameterKey(parameter_key)
    return (idx, 0)  # successfully created

  def DeleteObject(self, object_name, parameter_key):
    """Delete an object and its sub-objects/parameters."""
    raise NotImplementedError()

  def Download(self, command_key, file_type, url,
               username, password, file_size, target_filename,
               delay_seconds, success_url, failure_url):
    """Initiate a download immediately or after a delay."""
    raise NotImplementedError()

  def Reboot(self, command_key):
    """Reboot the CPE."""
    self.acs.Inform(command_key)

  def GetQueuedTransfers(self):
    """Retrieve a list of queued file transfers (downloads and uploads)."""
    raise NotImplementedError()

  def ScheduleInform(self, delay_seconds, command_key):
    """Request that this CPE call acs.Inform() at some point in the future."""
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
    raise NotImplementedError()

  def ScheduleDownload(self, command_key, file_type, url,
                       username, password, file_size, target_filename,
                       time_window_list):
    """Schedule a download for some time in the future."""
    raise NotImplementedError()

  def CancelTransfer(self, command_key):
    """Cancel a scheduled file transfer."""
    raise NotImplementedError()

  def ChangeDUState(self, operations, command_key):
    """Trigger an install, update, or uninstall operation."""
    raise NotImplementedError()
