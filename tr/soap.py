#!/usr/bin/python
# Copyright 2011 Google Inc. All Rights Reserved.
#
"""Encodings for the SOAP-based protocol used by TR-069."""

__author__ = 'apenwarr@google.com (Avery Pennarun)'


import xmlwitch


class FaultType(object):
  SERVER = 'Server'
  CLIENT = 'Client'


class CpeFault(object):
  METHOD_NOT_SUPPORTED = 9000, FaultType.SERVER
  REQUEST_DENIED = 9001, FaultType.SERVER
  INTERNAL_ERROR = 9002, FaultType.SERVER
  INVALID_ARGUMENTS = 9003, FaultType.CLIENT
  RESOURCES_EXCEEDED = 9004, FaultType.SERVER
  INVALID_PARAM_NAME = 9005, FaultType.CLIENT
  INVALID_PARAM_TYPE = 9006, FaultType.CLIENT
  INVALID_PARAM_VALUE= 9007, FaultType.CLIENT
  NON_WRITABLE_PARAM = 9008, FaultType.CLIENT
  NOTIFICATION_REQUEST_REJECTED = 9009, FaultType.SERVER
  DOWNLOAD_FAILURE = 9010, FaultType.SERVER
  UPLOAD_FAILURE = 9011, FaultType.SERVER
  FILE_TRANSFER_AUTH = 9012, FaultType.SERVER
  FILE_TRANSFER_PROTOCOL = 9013, FaultType.SERVER
  DOWNLOAD_MULTICAST = 9014, FaultType.SERVER
  DOWNLOAD_CONNECT = 9015, FaultType.SERVER
  DOWNLOAD_ACCESS = 9016, FaultType.SERVER
  DOWNLOAD_INCOMPLETE = 9017, FaultType.SERVER
  DOWNLOAD_CORRUPTED = 9018, FaultType.SERVER
  DOWNLOAD_AUTH = 9019, FaultType.SERVER
  # codes 9800-9899: vendor-defined faults


class AcsFault(object):
  METHOD_NOT_SUPPORTED = 8000, FaultType.SERVER
  REQUEST_DENIED = 8001, FaultType.SERVER
  INTERNAL_ERROR = 8002, FaultType.SERVER
  INVALID_ARGUMENTS = 8003, FaultType.CLIENT
  RESOURCES_EXCEEDED = 8004, FaultType.SERVER
  RETRY_REQUEST = 8005, FaultType.SERVER
  # codes 8800-8899: vendor-defined faults


class _Enterable(object):
  def __init__(self, iterable):
    self.iter = iterable

  def __iter__(self):
    return self.iter

  def __enter__(self):
    return self.iter.next()

  def __exit__(self, type, value, tb):
    try:
      self.iter.next()
    except StopIteration:
      pass


def Enterable(func):
  def Wrap(*args, **kwargs):
    return _Enterable(func(*args, **kwargs))
  return Wrap


@Enterable
def Envelope(request_id, hold_requests):
  xml = xmlwitch.Builder(version='1.0', encoding='utf-8')
  attrs = { 'xmlns:soap': 'http://schemas.xmlsoap.org/soap/envelope/',
            'xmlns:soap-enc': 'http://schemas.xmlsoap.org/soap/encoding/',
            'xmlns:xsd': 'http://www.w3.org/2001/XMLSchema',
            'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
            'xmlns:cwmp': 'urn:dslforum-org:cwmp-1-1' }
  with xml['soap:Envelope'](**attrs):
    with xml['soap:Header']:
      must_understand_attrs = { 'soap:mustUnderstand': '1' }
      if request_id is not None:
        xml['cwmp:ID'](str(request_id), **must_understand_attrs)
      if hold_requests is not None:
        xml['cwmp:HoldRequests'](hold_requests and '1' or '0',
                                 **must_understand_attrs)
    with xml['soap:Body']:
      yield xml


@Enterable
def Fault(xml, fault, faultstring):
  fault_code, fault_type = fault
  with xml['soap:Fault']:
    xml.faultcode(fault_type)
    xml.faultstring('CWMP Fault')
    with xml.detail:
      with xml['cwmp:Fault']:
        xml.FaultCode(str(fault_code))
        xml.FaultString(faultstring)
        yield xml


def GetParameterNames(xml, path, nextlevel):
  with xml['cwmp:GetParameterNames']:
    xml.ParameterPath(path)
    xml.NextLevel(nextlevel and '1' or '0')
  return xml


def SetParameterValuesFault(xml, faults):
  with Fault(xml, CpeFault.INVALID_ARGUMENTS, 'Invalid arguments') as xml:
    for parameter, code, string in faults:
      with xml.SetParameterValuesFault:
        xml.ParameterName(parameter)
        xml.FaultCode(str(int(code[0])))
        xml.FaultString(string)
  return xml


def main():
  with Envelope(1234, False) as xml:
    print GetParameterNames(xml, 'System.', 1)
  with Envelope(None, None) as xml:
    print SetParameterValuesFault(xml,
                                  [('Object.x.y', CpeFault.INVALID_PARAM_TYPE, 'stupid error'),
                                   ('Object.y.z', CpeFault.INVALID_PARAM_NAME, 'blah error')])
                                 


if __name__ == '__main__':
  main()

