"""Unit Tests for diagui.py implementation."""

__author__ = 'anandkhare@google.com (Anand Khare)'

import ast
import unittest
import google3
import diagui.main
import tornado.httpclient
import tr.mainloop


class AsynchFetch(object):
  """Creates instance of client object, makes asynchronous calls to server."""

  def __init__(self, url_temp):
    self.http_client = tornado.httpclient.AsyncHTTPClient()
    self.resp = None
    self.http_client.fetch(url_temp, method='GET',
                           callback=self.HandleRequest)

  def HandleRequest(self, response):
    self.resp = response

  def ReturnResponseBody(self):
    return self.resp.body


class DiaguiTest(unittest.TestCase):
  """Tests whether 2 clients receive the same data from the server.

     Also checks if both receive updates.
  """

  def setUp(self):
    self.checksum = '0'
    self.url_string = 'http://localhost:8880/content.json?checksum='

  def testUpdateDict(self):
    test_data = """acs OK (May 21 2013 18:58:41+700)
softversion 1.16a
uptime 76:28:39
temperature 54 C
fiberjack Up
wanmac 1a:2b:3c:4d:5e:6f
wanip 63.28.214.97
lanip 192.168.1.1
subnetmask 255.255.255.0
dhcpstart 192.158.1.100
dhcpend 192.168.1.254
wiredlanmac 6a:5b:4c:3d:2e:1f
wiredlanstatus Up
wireddevices Living Room (TV box, 6a:5b:4c:3d:2e:1f)
ssid24 AllenFamilyNetwork
ssid5 (same)
wpa2 (configured)
wirelesslanmac 3a:1b:4c:1d:5e:9f
wirelesslanstatus Up
wirelessdevices Dad\'s Phone (6a:5b:4c:3d:2e:1f)
upnp O
portforwarding 80-80: Dad\'s Computer (6a:5b:4c:3d:2e:1f)
dmzdevice Wireless Device (1) (6a:5b:4c:3d:2e:1f)
dyndns DynDNS
username allenfamily
domain home.allenfamily.com
"""
    f = open('Testdata/testdata', 'w')
    f.write(test_data)
    f.close()
    url_temp = self.url_string + self.checksum
    app = diagui.main.DiaguiSettings()
    app.listen(8880)
    response1 = AsynchFetch(url_temp)
    response2 = AsynchFetch(url_temp)
    tr.mainloop.MainLoop().Start(1)
    self.assertEqual(response1.ReturnResponseBody(),
                     response2.ReturnResponseBody())
    self.checksum = ast.literal_eval(response1.ReturnResponseBody()).get(
        'checksum')
    test_data = """acs OK (May 21 2013 18:58:41+700)
softversion 2.16a
uptime 76:28:39
temperature 54 C
fiberjack Up
wanmac 1a:2b:3c:4d:5e:6f
wanip 63.28.214.97
lanip 192.168.1.1
subnetmask 255.255.255.0
dhcpstart 192.158.1.100
dhcpend 192.168.1.254
wiredlanmac 6a:5b:4c:3d:2e:1f
wiredlanstatus Up
wireddevices Living Room (TV box, 6a:5b:4c:3d:2e:1f)
ssid24 AllenFamilyNetwork
ssid5 (same)
wpa2 (configured)
wirelesslanmac 3a:1b:4c:1d:5e:9f
wirelesslanstatus Up
wirelessdevices Dad\'s Phone (6a:5b:4c:3d:2e:1f)
upnp O
portforwarding 80-80: Dad\'s Computer (6a:5b:4c:3d:2e:1f)
dmzdevice Wireless Device (1) (6a:5b:4c:3d:2e:1f)
dyndns DynDNS
username allenfamily
domain home.allenfamily.com
"""
    f = open('Testdata/testdata', 'w')
    f.write(test_data)
    f.close()
    url_temp = self.url_string + self.checksum
    response1_new = AsynchFetch(url_temp)
    response2_new = AsynchFetch(url_temp)
    tr.mainloop.MainLoop().Start(1)
    self.assertEqual(response1_new.ReturnResponseBody(),
                     response2_new.ReturnResponseBody())

    self.assertNotEqual(response1.ReturnResponseBody(),
                        response1_new.ReturnResponseBody())


if __name__ == '__main__':
  unittest.main()
