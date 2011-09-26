#!/usr/bin/python
# Copyright 2011 Google Inc. All Rights Reserved.
#
"""Mappings from api.ACS and api.CPE to SOAP encodings."""

__author__ = 'apenwarr@google.com (Avery Pennarun)'


import api
import soap


class TR069Service(object):
  def __init__(self, impl):
    self.impl = impl
    self.out_queue = []

  def send(self, xml, immediate, callback):
    xml = str(xml)
    if immediate:
      self.out_queue.insert(0, (xml, True, callback))
    else:
      self.out_queue.append((xml, False, callback))

  def pop(self, hold_requests):
    for i in len(self.out_queue):
      xml, override_hold = self.out_queue[i]
      if override_hold or not hold_requests:
        self.out_queue.pop(i)
        return xml

  def handle(self, obj):
    pass

  def GetRPCMethodsRequest(self, obj):
    with soap.Envelope(1234, None) as xml:
      with xml['cwmp:GetRPCMethodsResponse']:
        with xml.MethodList:
          for method in self.impl.GetRPCMethods():
            xml.string(method)
    self.send(xml, immediate=True, callback=None)

  def GetRPCMethodsResponse(self, obj):
    print obj


class ACS(TR069Service):
  def __init__(self, acs):
    TR069Service.__init__(self, impl=acs)


class CPE(TR069Service):
  def __init__(self, cpe):
    TR069Service.__init__(self, impl=cpe)


def main():
  import core
  real_acs = api.ACS()
  real_cpe = api.CPE(real_acs, core.Exporter())
  acs = ACS(real_acs)
  cpe = CPE(real_cpe)
  acs.DoGetRPCMethods(None)


if __name__ == '__main__':
  main()
