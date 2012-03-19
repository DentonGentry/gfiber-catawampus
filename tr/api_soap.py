#!/usr/bin/python
# Copyright 2011 Google Inc. All Rights Reserved.
#
"""Mappings from api.ACS and api.CPE to SOAP encodings."""

__author__ = 'apenwarr@google.com (Avery Pennarun)'

import time

import google3
import api
import core
import cwmpbool
import cwmpdate
import soap


class Encode(object):
  def __init__(self):
    self.request_id = 'catawampus.{0!r}'.format(time.time())
    self.hold_requests = None

  def _Envelope(self):
    return soap.Envelope(self.request_id, self.hold_requests)

  def GetRPCMethods(self):
    with self._Envelope() as xml:
      xml['cwmp:GetRPCMethods'](None)
    return xml

  def Inform(self, root, events=[], max_envelopes=1,
             current_time=time.time(), retry_count=0, parameter_list=[]):
    with self._Envelope() as xml:
      with xml['cwmp:Inform']:
        with xml.DeviceId:
          try:
            di = root.GetExport('Device.DeviceInfo')
          except AttributeError:
            di = root.GetExport('InternetGatewayDevice.DeviceInfo')
          xml.Manufacturer(di.Manufacturer)
          xml.OUI(di.ManufacturerOUI)
          xml.ProductClass(di.ProductClass)
          xml.SerialNumber(di.SerialNumber)
        soaptype = "EventStruct[{0}]".format(len(events))
        event_attrs = { 'soap-enc:arrayType': soaptype }
        with xml.Event(**event_attrs):
          for event in events:
            with xml.EventStruct:
              xml.EventCode(str(event[0]))
              if event[1] is not None:
                xml.CommandKey(str(event[1]))
              else:
                xml.CommandKey(None)
        xml.MaxEnvelopes(str(max_envelopes))
        xml.CurrentTime(cwmpdate.format(current_time))
        xml.RetryCount(str(retry_count))
        soaptype = "cwmp:ParameterValueStruct[{0}]".format(len(parameter_list))
        parameter_list_attrs = { 'soap-enc:arrayType': soaptype }
        with xml.ParameterList(**parameter_list_attrs):
          for name, value in parameter_list:
            with xml.ParameterValueStruct:
              xml.Name(name)
              xml.Value(str(value), xsi__type="xsd:string")
    return xml

  def GetParameterNames(self, parameter_path, next_level_only):
    with self._Envelope() as xml:
      with xml['cwmp:GetParameterNames']:
        xml.ParameterPath(parameter_path)
        xml.NextLevel(next_level_only and '1' or '0')
    return xml

  def GetParameterValues(self, parameter_names):
    with self._Envelope() as xml:
      with xml['cwmp:GetParameterValues']:
        with xml.ParameterNames:
          for name in parameter_names:
            xml.string(name)
    return xml

  def SetParameterValues(self, parameter_list, parameter_key):
    with self._Envelope() as xml:
      with xml['cwmp:SetParameterValues']:
        soaptype = "cwmp:ParameterValueStruct[{0}]".format(len(parameter_list))
        parameter_list_attrs = { 'soap-enc:arrayType': soaptype }
        with xml.ParameterList(**parameter_list_attrs):
          for name, value in parameter_list:
            with xml.ParameterValueStruct:
              xml.Name(str(name))
              xml.Value(str(value))
        xml.ParameterKey(str(parameter_key))
    return xml

  def AddObject(self, object_name, parameter_key):
    with self._Envelope() as xml:
      with xml['cwmp:AddObject']:
        xml.ObjectName(str(object_name))
        xml.ParameterKey(str(parameter_key))
    return xml

  def DeleteObject(self, object_name, parameter_key):
    with self._Envelope() as xml:
      with xml['cwmp:DeleteObject']:
        xml.ObjectName(str(object_name))
        xml.ParameterKey(str(parameter_key))
    return xml

  def TransferComplete(self, command_key, faultcode, faultstring,
                       starttime=None, endtime=None):
    with self._Envelope() as xml:
      with xml['cwmp:TransferComplete']:
        xml.CommandKey(str(command_key))
        with xml['FaultStruct']:
          xml.FaultCode(str(faultcode))
          xml.FaultString(str(faultstring))
        xml.StartTime(cwmpdate.format(starttime))
        xml.CompleteTime(cwmpdate.format(endtime))
    return xml


class ParameterNameError(AttributeError):
  pass


class SoapHandler(object):
  def __init__(self, impl):
    self.impl = impl

  def _ExceptionListToFaultList(self, errors):
    """Generate a list of Soap Faults for SetParameterValues.

    Turn a list of api.Parameter{Type,Value}Exception objects returned
    from api.SetParameterValues into a list suitable for
    soap.SetParameterValuesFault.
    """
    faults = []
    for error in errors:
      if isinstance(error, api.ParameterTypeError):
        code = soap.CpeFault.INVALID_PARAM_TYPE
      elif isinstance(error, api.ParameterValueError):
        code = soap.CpeFault.INVALID_PARAM_VALUE
      else:
        code = soap.CpeFault.INTERNAL_ERROR
      faults.append((error.parameter, code, str(error)))
    return faults

  def Handle(self, body):
    body = str(body)
    obj = soap.Parse(body)
    request_id = obj.Header.get('ID', None)
    req = obj.Body[0]
    method = req.name
    with soap.Envelope(request_id, None) as xml:
      try:
        responder = self._GetResponder(method)
        result = responder(xml, req)
      except KeyError as e:
        result = soap.SimpleFault(
            xml, cpefault=soap.CpeFault.INVALID_PARAM_NAME,
            faultstring='No such parameter: %s' % e.args[0])
      except IndexError as e:
        result = soap.SimpleFault(
            xml, cpefault=soap.CpeFault.INVALID_ARGUMENTS,
            faultstring=str(e))
      except NotImplementedError:
        cpefault = soap.CpeFault.METHOD_NOT_SUPPORTED
        faultstring = 'Unsupported RPC method: %s' % method
        result = soap.SimpleFault(xml, cpefault, faultstring)
      except ParameterNameError as e:
        result = soap.SimpleFault(
            xml, cpefault=soap.CpeFault.INVALID_PARAM_NAME,
            faultstring=str(e))
      except api.ParameterTypeError as e:
        result = soap.SetParameterValuesFault(
            xml, [(e.parameter, soap.CpeFault.INVALID_PARAM_TYPE, str(e))])
      except api.ParameterValueError as e:
        result = soap.SetParameterValuesFault(
            xml, [(e.parameter, soap.CpeFault.INVALID_PARAM_VALUE, str(e))])
      except api.SetParameterErrors as e:
        faults = self._ExceptionListToFaultList(e.error_list)
        result = soap.SetParameterValuesFault(xml, faults)

    if result is not None:
      return xml
    else:
      return None

  def _GetResponder(self, method):
    try:
      return getattr(self, method)
    except:
      raise NotImplementedError()

  def GetRPCMethods(self, xml, req):
    with xml['cwmp:GetRPCMethodsResponse']:
      with xml.MethodList:
        for method in self.impl.GetRPCMethods():
          xml.string(method)
    return xml


class ACS(SoapHandler):
  def __init__(self, acs):
    SoapHandler.__init__(self, impl=acs)

  def Inform(self, xml, req):
    with xml['cwmp:InformResponse']:
      self.impl.Inform(None, req.DeviceId, req.Event, req.MaxEnvelopes,
                       req.CurrentTime, req.RetryCount, req.ParameterList)
      xml.MaxEnvelopes(str(1))
    return xml


class CPE(SoapHandler):
  def __init__(self, cpe):
    SoapHandler.__init__(self, impl=cpe)

  def InformResponse(self, xml, req):
    self.impl.informResponseReceived()
    return None

  def GetParameterNames(self, xml, req):
    path = str(req.ParameterPath)
    if path.endswith('.'):
      path = path[:-1]
    nextlevel = cwmpbool.parse(req.NextLevel)
    names = list(self.impl.GetParameterNames(path, nextlevel))
    soaptype = "ParameterInfoStruct[{0}]".format(len(names))
    parameter_list_attrs = { 'soap-enc:arrayType': soaptype }
    with xml['cwmp:GetParameterNamesResponse']:
      with xml.ParameterList(**parameter_list_attrs):
        for name in names:
          with xml['ParameterInfoStruct']:
            xml.Name(name)
            xml.Writable('1')  # TODO(apenwarr): detect true writability here
    return xml

  def GetParameterValues(self, xml, req):
    names = [str(i) for i in req.ParameterNames]
    values = self.impl.GetParameterValues(names)
    soaptype = "cwmp:ParameterValueStruct[{0}]".format(len(values))
    parameter_list_attrs = { 'soap-enc:arrayType': soaptype }
    with xml['cwmp:GetParameterValuesResponse']:
      with xml.ParameterList(**parameter_list_attrs):
        for name, value in values:
          with xml.ParameterValueStruct:
            xml.Name(name)
            xml.Value(str(value), xsi__type="xsd:string")
    return xml

  def SetParameterValues(self, xml, req):
    names = [(str(p[0]), str(p[1])) for p in req.ParameterList]
    code = self.impl.SetParameterValues(names, req.ParameterKey)
    with xml['cwmp:SetParameterValuesResponse']:
      xml.Status(str(int(code)))
    return xml

  def _CheckObjectName(self, name):
    if not name.endswith('.'):
      raise ParameterNameError('ObjectName must end in period: %s' % name)

  def AddObject(self, xml, req):
    self._CheckObjectName(req.ObjectName)
    idx, status = self.impl.AddObject(req.ObjectName, req.ParameterKey)
    with xml['cwmp:AddObjectResponse']:
      xml.InstanceNumber(str(idx))
      xml.Status(str(int(status)))
    return xml

  def DeleteObject(self, xml, req):
    self._CheckObjectName(req.ObjectName)
    code = self.impl.DeleteObject(req.ObjectName, req.ParameterKey)
    with xml['cwmp:DeleteObjectResponse']:
      xml.Status(str(int(code)))
    return xml

  def Download(self, xml, req):
    try:
      username = req.Username
      password = req.Password
    except:
      username = password = None

    try:
      (code, starttime, endtime) = self.impl.Download(
          command_key=req.CommandKey, file_type=req.FileType,
          url=req.URL, username=username, password=password,
          file_size=int(req.FileSize), target_filename=req.TargetFileName,
          delay_seconds=int(req.DelaySeconds),
          success_url=req.SuccessURL, failure_url=req.FailureURL)
    except core.ResourcesExceededError as e:
      return soap.SimpleFault(xml, soap.CpeFault.RESOURCES_EXCEEDED, str(e))
    except core.FileTransferProtocolError as e:
      return soap.SimpleFault(xml, soap.CpeFault.FILE_TRANSFER_PROTOCOL, str(e))

    with xml['cwmp:DownloadResponse']:
      xml.Status(str(code))
      xml.StartTime(cwmpdate.format(starttime))
      xml.CompleteTime(cwmpdate.format(endtime))
    return xml

  def TransferCompleteResponse(self, xml, req):
    """Response to a TransferComplete sent by the CPE."""
    self.impl.transferCompleteResponseReceived()
    return None

  def GetQueuedTransfers(self, xml, req):
    transfers = self.impl.GetAllQueuedTransfers()
    with xml['cwmp:GetQueuedTransfersResponse']:
      for q in transfers:
        with xml['TransferList']:
          xml.CommandKey(q.CommandKey)
          xml.State(str(q.State))
    return xml

  def GetAllQueuedTransfers(self, xml, req):
    transfers = self.impl.GetAllQueuedTransfers()
    with xml['cwmp:GetAllQueuedTransfersResponse']:
      for q in transfers:
        with xml['TransferList']:
          xml.CommandKey(q.CommandKey)
          xml.State(str(q.State))
          xml.IsDownload(str(q.IsDownload))
          xml.FileType(str(q.FileType))
          xml.FileSize(str(q.FileSize))
          xml.TargetFileName(str(q.TargetFileName))
    return xml

  def CancelTransfer(self, xml, req):
    try:
      self.impl.CancelTransfer(req.CommandKey)
    except core.CancelNotPermitted as e:
      return soap.SimpleFault(xml, soap.CpeFault.DOWNLOAD_CANCEL_NOTPERMITTED,
                              str(e))
    xml['cwmp:CancelTransferResponse'](None)
    return xml


def main():
  class FakeDeviceInfo(object):
    Manufacturer = "manufacturer"
    ManufacturerOUI = "oui"
    ProductClass = "productclass"
    SerialNumber = "serialnumber"

  root = core.Exporter()
  root.Export(params=['Test', 'Test2'], lists=['Sub'])
  root.Test = '5'
  root.Test2 = 6
  root.SubList = {}
  root.Sub = core.Exporter
  root.DeviceInfo = FakeDeviceInfo()

  real_acs = api.ACS()
  real_cpe = api.CPE(real_acs, root, None)
  cpe = CPE(real_cpe)
  acs = ACS(real_acs)
  encode = Encode()
  print cpe.Handle(encode.GetRPCMethods())
  print cpe.Handle(encode.GetParameterNames('', False))
  print cpe.Handle(encode.GetParameterValues(['Test']))
  print cpe.Handle(encode.SetParameterValues([('Test', 6),('Test2', 7)],
                                             77))
  print cpe.Handle(encode.GetParameterValues(['Test', 'Test2']))
  print cpe.Handle(encode.AddObject('Sub.', 5))
  print cpe.Handle(encode.DeleteObject('Sub.0', 5))
  print acs.Handle(encode.Inform(root, [], 1, None, 1, []))


if __name__ == '__main__':
  main()
