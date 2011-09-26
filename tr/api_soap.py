#!/usr/bin/python
# Copyright 2011 Google Inc. All Rights Reserved.
#
"""Mappings from api.ACS and api.CPE to SOAP encodings."""

__author__ = 'apenwarr@google.com (Avery Pennarun)'


import api
import soap


class SoapHandler(object):
  def __init__(self, impl):
    self.impl = impl
    #self.out_queue = []

  def TODO_send(self, xml, immediate, callback):
    xml = str(xml)
    if immediate:
      self.out_queue.insert(0, (xml, True, callback))
    else:
      self.out_queue.append((xml, False, callback))

  def TODO_pop(self, hold_requests):
    for i in len(self.out_queue):
      xml, override_hold = self.out_queue[i]
      if override_hold or not hold_requests:
        self.out_queue.pop(i)
        return xml

  def Handle(self, body):
    obj = soap.Parse(body)
    request_id = obj.Header.get('ID', None)
    req = obj.Body[0]
    reqname = req.name
    if not reqname.endswith('Response'):
      reqname += 'Request'
    return str(getattr(self, reqname)(request_id, req))

  def GetRPCMethodsRequest(self, request_id, req):
    with soap.Envelope(request_id, None) as xml:
      with xml['cwmp:GetRPCMethodsResponse']:
        with xml.MethodList:
          for method in self.impl.GetRPCMethods():
            xml.string(method)
    return xml


class ACS(SoapHandler):
  def __init__(self, acs):
    SoapHandler.__init__(self, impl=acs)

  def GetRPCMethodsResponse(self, obj):
    print obj


class CPE(SoapHandler):
  def __init__(self, cpe):
    SoapHandler.__init__(self, impl=cpe)

  def GetParameterNamesRequest(self, request_id, req):
    names = self.impl.GetParameterNames(str(req.ParameterPath),
                                        int(req.NextLevel))
    with soap.Envelope(request_id=request_id, hold_requests=None) as xml:
      with xml['cwmp:GetParameterNamesResponse']:
        for name in names:
          with xml['ParameterInfoStruct']:
            xml.Name(name)
            xml.Writable('1')  # TODO(apenwarr): detect true writability here
    return xml


def main():
  import core
  real_acs = api.ACS()
  real_cpe = api.CPE(real_acs, core.Exporter())
  acs = ACS(real_acs)
  cpe = CPE(real_cpe)
  acs.DoGetRPCMethods(None)


if __name__ == '__main__':
  main()
