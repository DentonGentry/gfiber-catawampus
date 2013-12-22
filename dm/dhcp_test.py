#!/usr/bin/python
# Copyright 2013 Google Inc. All Rights Reserved.
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

# unittest requires method names starting in 'test'
# pylint: disable-msg=C6409

"""Unit tests for dhcp.py implementation."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import google3
import unittest
import tr.cwmpdate
import dhcp


class DhcpTest(unittest.TestCase):
  """Tests for dhcp.py."""

  def testClient(self):
    client = dhcp.Client(ipaddr='1.2.3.4', chaddr='00:01:02:03:04:05',
                         expiry=1389022961, clientid='clientid_1',
                         hostname='hostname_1', userclassid='userclassid_1',
                         vendorclassid='vendorclassid_1')
    self.assertEqual(client.Chaddr, '00:01:02:03:04:05')
    self.assertEqual(client.IPv4AddressNumberOfEntries, 1)
    client.AddIP(ipaddr='1.2.3.5', expiry=1389022962)
    self.assertEqual(client.IPv4AddressNumberOfEntries, 2)
    self.assertEqual(client.IPv4AddressList['1'].IPAddress, '1.2.3.4')
    d = tr.cwmpdate.format(client.IPv4AddressList['1'].LeaseTimeRemaining)
    self.assertEqual(d, '2014-01-06T15:42:41Z')
    self.assertEqual(client.IPv4AddressList['2'].IPAddress, '1.2.3.5')
    d = tr.cwmpdate.format(client.IPv4AddressList['2'].LeaseTimeRemaining)
    self.assertEqual(d, '2014-01-06T15:42:42Z')
    self.assertEqual(client.OptionNumberOfEntries, 4)
    self.assertEqual(client.OptionList['1'].Tag, dhcp.CL)
    self.assertEqual(client.OptionList['1'].Value, 'clientid_1')
    self.assertEqual(client.OptionList['2'].Tag, dhcp.HN)
    self.assertEqual(client.OptionList['2'].Value, 'hostname_1')
    self.assertEqual(client.OptionList['3'].Tag, dhcp.UC)
    self.assertEqual(client.OptionList['3'].Value, 'userclassid_1')
    self.assertEqual(client.OptionList['4'].Tag, dhcp.VC)
    self.assertEqual(client.OptionList['4'].Value, 'vendorclassid_1')
    client.ValidateExports()


if __name__ == '__main__':
  unittest.main()
