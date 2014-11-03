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

"""External API for TR-069 support.

The classes here represent the ACS (Auto Configuration Server) and CPE
(Customer Premises Equipment) endpoints in the TR-069 standard API.  You can
hand them an hierarchy of tr.core.Exporter and use the
TR-069 access methods to manipulate it.

This file doesn't implement the XML (SOAP-like) wrapper around the TR-069
API calls; it's just a python version of the API.
"""

__author__ = 'apenwarr@google.com (Avery Pennarun)'

import datetime

import tornado.ioloop
import tr.cwmpbool
import tr.cwmptypes
import download

# Time in seconds to refetch the values that are being watched
# for notifications.
REFRESH_TIMEOUT = 60

# TR69 constants for which notification method to use.
PASSIVE_NOTIFY = 1
ACTIVE_NOTIFY = 2


class SetParameterErrors(Exception):
  """Exceptions which occurred during a SetParameterValues transaction."""

  def __init__(self, error_list, msg):
    Exception.__init__(self, '%s (%s)' % (msg, error_list))
    self.error_list = error_list


class ParameterNameError(KeyError):
  """Raised for SetParameterValue/GetParameterNames to nonexistant parameter."""

  def __init__(self, parameter, msg):
    KeyError.__init__(self, msg)
    self.parameter = parameter


class ParameterTypeError(TypeError):
  """Raised when a SetParameterValue has the wrong type."""

  def __init__(self, parameter, msg):
    TypeError.__init__(self, msg)
    self.parameter = parameter


class ParameterValueError(ValueError):
  """Raised when a SetParameterValue has an invalid value."""

  def __init__(self, parameter, msg):
    ValueError.__init__(self, msg)
    self.parameter = parameter


class ParameterNotWritableError(AttributeError):
  """Raised when a SetParameterValue tries to set a read-only parameter."""

  def __init__(self, parameter, msg):
    AttributeError.__init__(self, msg)
    self.parameter = parameter


class AddObjectsErrors(Exception):
  """Exceptions which occurred during an AddObjects transaction."""

  def __init__(self, error_list, msg):
    Exception.__init__(self, '%s (%s)' % (msg, error_list))
    self.error_list = error_list


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

  def Inform(self, cpe, unused_root, unused_events, unused_max_envelopes,
             unused_current_time, unused_retry_count, unused_parameter_list):
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


class ParameterAttributes(object):
  """This is a side object that contains all of the attribute settings.

  TR69 defines the following parameters of which we really only
  care about 'Notification':
    Name (is the key)
    NotificationChange (if set to True allow Notification to change)
    Notification
    AccessListChange
    AccessList

  AccessList is kept in the value dict just for tr69 compatibility, the
  only allowed value in the spec is "Subscriber".

  There is also one timer that fires every minute to check for attributes
  that have triggered.
  """

  class Attributes(object):
    """Helper class to hold tr69 parameter attributes."""

    def __init__(self):
      self.current_value = None
      self.notification = 0
      self.access_list = None

  def __init__(self, root, ioloop):
    self.ioloop = ioloop
    self.params = dict()
    self.root = root
    self.set_notification_cb = None
    self.new_value_change_session_cb = None
    self.timeout = self.ioloop.add_timeout(
        datetime.timedelta(0, REFRESH_TIMEOUT), self.CheckForTriggers)

  def ClearParameterAttributes(self, name):
    """Clear the attributes for a parameter.

    Args:
      name: The parameter having its attributes removed.
    """
    if name.endswith('.'):
      # delete all the child objects that have this name as prefix.
      children = [x for x in self.params.keys() if x.startswith(name)]
      for child in children:
        del self.params[child]
      name = name[:-1]  # clear the '.' off the end.
    if name in self.params:
      del self.params[name]

  def SetParameterAttributes(self, attrs):
    """Set Attributes for a parameter.

    The only attributes that are supported are:
      Notification
      AccessList.

    Args:
      attrs: key/value pairs of attribute names and their values.
    Returns:
      None

    Raises:
      ValueError: if attrs doesn't contain a name.
    """
    if 'Name' not in attrs:
      raise ValueError('SetParameterAttributes must have a "Name" attribute.')
    name = attrs['Name']

    if name not in self.params:
      self.params[name] = ParameterAttributes.Attributes()

    if ('Notification' in attrs and
        'NotificationChange' in attrs and
        tr.cwmpbool.parse(attrs['NotificationChange'])):
      self.params[name].notification = int(attrs['Notification'])

    if ('AccessList' in attrs and
        'AccessListChange' in attrs and
        tr.cwmpbool.parse(attrs['AccessListChange'])):
      self.params[name].access_list = str(attrs['AccessList'])

    # Finally store the initial value so changes can be watched for.
    self.params[name].current_value = self.root.GetExport(name)

  def GetParameterAttribute(self, name, attr):
    """Retrieve the given attribute for the parameter name."""
    if name not in self.params:
      self.params[name] = ParameterAttributes.Attributes()

    if attr == 'Notification':
      return self.params[name].notification
    if attr == 'AccessList':
      return self.params[name].access_list
    raise ValueError('Attribute %s is not supported.' % attr)

  def CheckForTriggers(self):
    """Checks if a notification needs to be sent to the ACS."""
    for paramname in self.params.keys():
      try:
        value = self.root.GetExport(paramname)
      except KeyError:
        # ACS sets notifications for ephemeral objects like Device.Hosts.Host.
        # The object doesn't exist right now, it clearly has no notifications.
        continue
      attrs = self.params[paramname]

      # This checks that the Notification attribute is set, and if it
      # is 1 (passive notification) or 2(active notification) sets the
      # parameter data to inform the ACS with.
      # And if the Notification is 2 (active) it will start a new session
      # with the ACS.
      # It is okay to call the set_notification_parameters_cb multiple
      # times, the caller will build up a list of all the parameters to
      # inform with.
      if ((attrs.notification == PASSIVE_NOTIFY or
           attrs.notification == ACTIVE_NOTIFY) and
          value != attrs.current_value and
          self.set_notification_parameters_cb):
        self.set_notification_parameters_cb([(paramname, value)])
        if (self.new_value_change_session_cb and
            attrs.notification == ACTIVE_NOTIFY):
          self.new_value_change_session_cb()
      attrs.current_value = value
    self.ioloop.remove_timeout(self.timeout)
    self.timeout = self.ioloop.add_timeout(
        datetime.timedelta(0, REFRESH_TIMEOUT), self.CheckForTriggers)


class CPE(TR069Service):
  """Represents a TR-069 CPE (Customer Premises Equipment)."""

  def __init__(self, root):
    TR069Service.__init__(self)
    self._last_parameter_key = ''
    self.root = root
    self.download_manager = download.DownloadManager()
    self.transfer_complete_received_cb = None
    self.inform_response_received_cb = None
    self.parameter_attrs = ParameterAttributes(
        root, tornado.ioloop.IOLoop.instance())

  # There's some magic here, functions that start with a capital letter
  # are assumed to be ACS invokable, for example 'SetParameterAttributes'
  # so this helper starts with a lower case letter.
  # pylint:disable=g-bad-name
  def setCallbacks(self, send_transfer_complete,
                   transfer_complete_received,
                   inform_response_received,
                   set_notification_parameters,
                   new_value_change_session):
    self.download_manager.send_transfer_complete = send_transfer_complete
    self.transfer_complete_received_cb = transfer_complete_received
    self.inform_response_received_cb = inform_response_received
    self.parameter_attrs.set_notification_parameters_cb = (
        set_notification_parameters)
    self.parameter_attrs.new_value_change_session_cb = new_value_change_session

  def startup(self):
    """Handle any initialization after reboot."""
    self.download_manager.RestoreDownloads()

  def _SetParameterKey(self, value):
    self._last_parameter_key = value

  def getParameterKey(self):
    return self._last_parameter_key

  def _SetParameterValue(self, name, value):
    """Given a parameter (which can include an object), set its value."""
    if name == 'ParameterKey':
      self._SetParameterKey(value)
      return None
    else:
      return self.root.SetExportParam(name, value)

  def _ConcludeTransaction(self, objects, do_commit):
    """Commit or abandon all pending writes.

    Args:
      objects: list of dirty objects to commit
      do_commit: call CommitTransaction if True, else AbandonTransaction

    Returns:
      The response code to return to ACS.

    SetParameterValues is an atomic transaction, all parameters are set or
    none of them are. We set obj.dirty and call obj.StartTransaction on
    every object written to. Now we walk back through the dirtied objects
    to finish the transaction.
    """
    # TODO(dgentry) At some point there will be interdependencies between
    #   objects. We'll need to develop a means to express those dependencies
    #   and walk the dirty objects in a specific order.
    for obj in objects:
      assert obj.dirty
      obj.dirty = False
      if do_commit:
        obj.CommitTransaction()
      else:
        obj.AbandonTransaction()
    return 0  # all values changed successfully

  @staticmethod
  def _Apply(error_list, fullname, attr_error, func, *args):
    try:
      return func(*args)
    except TypeError as e:
      error_list.append(ParameterTypeError(parameter=fullname, msg=str(e)))
    except ValueError as e:
      error_list.append(ParameterValueError(parameter=fullname, msg=str(e)))
    except KeyError as e:
      error_list.append(ParameterNameError(parameter=fullname, msg=str(e)))
    except AttributeError as e:
      # AttributeError might mean the attribute is missing, or that it's
      # read-only.  Since we call _Apply() to read the values first,
      # it means missing in that case.  If we get to the part where we start
      # writing values, it must mean read-only, because it wasn't missing
      # before.
      error_list.append(attr_error(parameter=fullname, msg=str(e)))

  def SetParameterValues(self, parameter_list, parameter_key):
    """Sets parameters on some objects."""
    parameter_list = list(parameter_list)
    error_list = []
    keys = []
    values = []
    for key, value in parameter_list:
      if key == 'ParameterKey':
        pass  # parameter_key overrides it anyhow
      else:
        keys.append(key)
        values.append(value)
    lookup = list(self.root.LookupExports(keys))

    # phase 1: grab existing values.
    oldvals = []
    for key, (obj, param) in zip(keys, lookup):
      oldvals.append(self._Apply(error_list, key, ParameterNameError,
                                 getattr, obj, param))
    if error_list:
      # don't need to _ConcludeTransaction since we didn't change anything yet
      raise SetParameterErrors(error_list=error_list,
                               msg='Transaction Errors: %d' % len(error_list))

    # phase 2: try validating new values.
    #  Since not all properties have validators, this won't catch all
    #  possible errors, but the more objects that support validators, the
    #  fewer transactions we'll have to rollback in the future.
    assert not error_list
    for key, (obj, param), value in zip(keys, lookup, values):
      self._Apply(error_list, key, ParameterNotWritableError,
                  tr.cwmptypes.tryattr, obj, param, value)
    if error_list:
      # don't need to _ConcludeTransaction since we didn't change anything yet
      raise SetParameterErrors(error_list=error_list,
                               msg='Transaction Errors: %d' % len(error_list))

    # phase 3: try setting new values.
    assert not error_list
    dirty = set()
    for key, (obj, param), value in zip(keys, lookup, values):
      self._Apply(error_list, key, ParameterNotWritableError,
                  obj.SetExportParam, param, value)
      dirty.add(obj)
    if error_list:
      # if there were *any* errors, need to undo *all* changes.
      # First reset all values to their recorded values.  (Some of them might
      # fail, but we can't do anything about that, so throw away the error
      # list.)
      for key, (obj, param), value, oldval in zip(keys, lookup,
                                                  values, oldvals):
        if oldval != value:
          self._Apply([], key, ParameterNotWritableError,
                      setattr, obj, param, oldval)
      # Now tell the objects themselves to undo the transactions, if they
      # support it.
      # TODO(apenwarr): Deprecate per-object transaction support.
      #  Once upon a time, we didn't have high-level transactions (ie. this
      #  function) so objects had to do it themselves, but it was very error
      #  prone.
      self._ConcludeTransaction(objects=dirty, do_commit=False)
      raise SetParameterErrors(error_list=error_list,
                               msg='Transaction Errors: %d' % len(error_list))

    # if we get here, all went well.
    assert not error_list
    self._SetParameterKey(parameter_key)
    return self._ConcludeTransaction(dirty, True)

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
    for param in parameter_names:
      if not param:
        # tr69 A.3.2.2: empty string indicates top of the name hierarchy.
        paramlist = self.root.ListExports(None, False)
        parameter_names.extend(paramlist)
      elif param.endswith('.'):
        paramlist = self.root.ListExports(param[:-1], False)
        for p in paramlist:
          parameter_names.append(param + p)
      else:
        try:
          result.append((param, self._GetParameterValue(param)))
        except KeyError:
          raise ParameterNameError(parameter=param, msg=param)
    return result

  def _JoinParamPath(self, parameter_path, param):
    if parameter_path:
      return '.'.join([parameter_path, param])
    else:
      return param

  def GetParameterNames(self, parameter_path, next_level_only):
    """Get the names of parameters or objects (possibly recursively)."""
    orig_path = parameter_path
    if parameter_path.endswith('.'):
      parameter_path = parameter_path[:-1]
    # First look up and find the parameter, if it doesn't exist we
    # need to raise an exception.  Spec: If the fault is caused by an
    # invalid ParameterPath value, the Invalid Parameter Name fault
    # code (9005) MUST be used instead of the more general Invalid
    # Arguments fault code(9003).  (An empty parameter_path is valid,
    # it means the root object)
    # spec: if ParameterPath were empty, with NextLevel equal true,
    # the response would list only IternetGatewayDevice. (if the CPE
    # is an Internet Gateway Device)
    if parameter_path:
      try:
        self.root.GetExport(parameter_path)
      except KeyError:
        # ParameterNameError will get changed into the proper tr-69 fault
        # 9005.
        # The second parameter is what gets sent back to ACS and has to be
        # the parameter name.
        raise ParameterNameError(parameter=orig_path, msg=orig_path)

    if not next_level_only and orig_path:
      # tr-69 A.3.2.3 If false, the response MUST contain the Parameter
      # or object whose name exactly matches the ParameterPath argument...
      yield orig_path
    exports = self.root.ListExports(parameter_path, not next_level_only)
    for param in exports:
      yield self._JoinParamPath(parameter_path, str(param))

  def SetParameterAttributes(self, attrs):
    """Set attributes (access control, notifications) on some parameters.

    The 'Name' parameter can either be the name for a single parameter
    or an object.  Alternatively this can be be a partial path name and
    indicates that all child parameters should have these parameters set.

    Args:
      attrs: A dict of parameters to set.
    """
    param = attrs['Name']
    if not self.root.SetExportAttrs(param, attrs):
      # TODO(jnewlin): Handle the case with the partial path.
      self.parameter_attrs.SetParameterAttributes(attrs)

  def GetParameterAttributes(self, parameter_names):
    """Get attributes (access control, notifications) on some parameters."""
    raise NotImplementedError()

  def AddObject(self, object_name, parameter_key):
    """Create a new object with default parameters."""
    assert object_name.endswith('.')
    (idx, _) = self.root.AddExportObject(object_name[:-1])
    self._SetParameterKey(parameter_key)
    return (idx, 0)  # successfully created

  def X_CATAWAMPUS_ORG_AddObjects(self, objcount_list, parameter_key):
    """Create several new objects with default parameters.

    This is not a standard method in TR-069, it's an extension we added.

    Args:
      objcount_list: a list of (object_name, count).  Each object_name ends
        in a dot.
      parameter_key: the tr-069 cookie used to check which commands completed.
    Returns:
      A tuple of (objindex_list, status).
      objindex_list: a list of (object_name, [indexes...]).
      status: 0 if successful.
    Raises:
      AddObjectsErrors: if any errors are encountered while adding objects.
    """
    out = []
    error_list = []
    for object_name, count in objcount_list:
      if not object_name.endswith('.'):
        error_list.append(ParameterNameError(
            parameter=object_name,
            msg='Object name must end with "."'))
        continue
      if count > 1000:
        error_list.append(ParameterValueError(
            parameter=object_name,
            msg='Tried to insert too many objects at once'))
        continue
      idxlist = []
      for _ in xrange(int(count)):
        idxo = self._Apply(error_list, object_name, ParameterNotWritableError,
                           self.root.AddExportObject, object_name[:-1])
        if not idxo:
          break
        (idx, _) = idxo
        idxlist.append(idx)
      out.append((object_name, idxlist))
    if error_list:
      # there are errors to report, which means we can't report the list of
      # added objects.  So we have to undo as many as the adds as we can
      # before returning the error.
      for object_name, idxlist in out:
        for idx in idxlist:
          self._Apply(error_list, object_name, ParameterNameError,
                      self.root.DeleteExportObject, object_name[:-1], idx)
        raise AddObjectsErrors(error_list=error_list,
                               msg='AddObjects Errors: %d' % len(error_list))
    self._SetParameterKey(parameter_key)
    return (out, 0)  # successfully created

  def DeleteObject(self, object_name, parameter_key):
    """Delete an object and its sub-objects/parameters."""
    assert object_name.endswith('.')
    self.parameter_attrs.ClearParameterAttributes(object_name)
    path = object_name.split('.')
    self.root.DeleteExportObject('.'.join(path[:-2]), path[-2])
    self._SetParameterKey(parameter_key)
    return 0  # successfully deleted

  def Download(self, command_key, file_type, url, username, password,
               file_size, target_filename, delay_seconds,
               success_url, failure_url):  # pylint:disable=unused-argument
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
    self.download_manager.Reboot(command_key)

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

  def transferCompleteResponseReceived(self):
    if self.transfer_complete_received_cb:
      self.transfer_complete_received_cb()
    return self.download_manager.TransferCompleteResponseReceived()

  def informResponseReceived(self):
    if self.inform_response_received_cb:
      self.inform_response_received_cb()
