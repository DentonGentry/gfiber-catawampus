"""Unit Tests for diagui.py implementation."""

__author__ = 'anandkhare@google.com (Anand Khare)'

import ast
import json
import os
import google3
import diagui.main
import tornado.httpclient
import tr.mainloop
import tr.helpers
import dm_root
from tr.wvtest import unittest


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
    self.save_activewan = diagui.main.ACTIVEWAN
    diagui.main.ACTIVEWAN = 'testdata/activewan'
    self.checksum = '0'
    self.url_string = 'http://localhost:8880/content.json?checksum='

  def tearDown(self):
    diagui.main.ACTIVEWAN = self.save_activewan

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
wiredlan 6a:5b:4c:3d:2e:1f Up
wireddevices Living Room (TV box, 6a:5b:4c:3d:2e:1f)
ssid24 AllenFamilyNetwork
ssid5 (same)
wpa2 (configured)
wirelesslan 3a:1b:4c:1d:5e:9f Up
wirelessdevices Dad\'s Phone (6a:5b:4c:3d:2e:1f)
upnp O
portforwarding 80-80: Dad\'s Computer (6a:5b:4c:3d:2e:1f)
dmzdevice Wireless Device (1) (6a:5b:4c:3d:2e:1f)
dyndns DynDNS
username allenfamily
domain home.allenfamily.com"""

    url_temp = self.url_string + self.checksum
    app = diagui.main.MainApplication(None, None)
    app.listen(8880)
    app.diagui.data = dict(line.decode('utf-8').strip().split(None, 1)
                           for line in test_data.split('\n'))
    app.diagui.UpdateCheckSum()
    response1 = AsynchFetch(url_temp)
    response2 = AsynchFetch(url_temp)
    main_loop = tr.mainloop.MainLoop()
    main_loop.Start(1)
    self.assertEqual(response1.ReturnResponseBody(),
                     response2.ReturnResponseBody())
    self.assertNotEqual(response1.ReturnResponseBody(), None)
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
wiredlan 6a:5b:4c:3d:2e:1f Up
wireddevices Living Room (TV box, 6a:5b:4c:3d:2e:1f)
ssid24 AllenFamilyNetwork
ssid5 (same)
wpa2 (configured)
wirelesslan 3a:1b:4c:1d:5e:9f Up
wirelessdevices Dad\'s Phone (6a:5b:4c:3d:2e:1f)
upnp O
portforwarding 80-80: Dad\'s Computer (6a:5b:4c:3d:2e:1f)
dmzdevice Wireless Device (1) (6a:5b:4c:3d:2e:1f)
dyndns DynDNS
username allenfamily
domain home.allenfamily.com"""
    app.diagui.data = dict(line.decode('utf-8').strip().split(None, 1)
                           for line in test_data.split('\n'))
    app.diagui.UpdateCheckSum()
    url_temp = self.url_string + self.checksum
    response1_new = AsynchFetch(url_temp)
    response2_new = AsynchFetch(url_temp)
    main_loop.Start(1)
    self.assertEqual(response1_new.ReturnResponseBody(),
                     response2_new.ReturnResponseBody())
    self.assertNotEqual(response1_new.ReturnResponseBody(), None)
    self.assertNotEqual(response1.ReturnResponseBody(),
                        response1_new.ReturnResponseBody())

  def testOnuStats(self):
    app = diagui.main.MainApplication(None, None)
    app.listen(8880)
    main_loop = tr.mainloop.MainLoop()
    diagui.main.ONU_STAT_FILE = 'testdata/onu_stats1.json'
    app.diagui.ReadOnuStats()
    self.assertTrue('onu_wan_connected' in app.diagui.data)
    self.assertFalse('onu_serial' in app.diagui.data)
    self.checksum = '0'
    url_temp = self.url_string + self.checksum
    response = AsynchFetch(url_temp)
    main_loop.Start(1)
    self.assertNotEqual(response.ReturnResponseBody(), None)
    jsdata = json.loads(response.ReturnResponseBody())
    self.assertTrue(jsdata['onu_wan_connected'])

    diagui.main.ONU_STAT_FILE = 'testdata/onu_stats2.json'
    app.diagui.ReadOnuStats()
    response = AsynchFetch(url_temp)
    main_loop.Start(1)
    jsdata = json.loads(response.ReturnResponseBody())
    self.assertTrue(jsdata['onu_wan_connected'])
    self.assertTrue(jsdata['onu_acs_contacted'])
    self.assertEqual(jsdata['onu_acs_contact_time'], 100000)
    self.assertEqual(jsdata['onu_serial'], '12345')


class TechuiTest(unittest.TestCase):
  """Tests the data gathering functions for the TechUI."""

  def testMainApp(self):
    app = diagui.main.MainApplication(None, None, True)
    fake_data = {'moca_bitloading': {},
                 'wifi_signal_strength': {},
                 'softversion': 'gfrg200-46-pre0-39-g056a912-th',
                 'other_aps': {'f4:f5:e8:80:58:d7': -67.0},
                 'host_names': {'ec:88:92:91:3d:67': 'android'},
                 'moca_corrected_codewords': {},
                 'moca_uncorrected_codewords': {},
                 'moca_signal_strength': {},
                 'self_signals': {'f4:f5:e8:83:01:94': -25},
                 'moca_nbas': {}}
    app.techui.data = fake_data
    app.listen(8880)
    main_loop = tr.mainloop.MainLoop()
    response = AsynchFetch('http://localhost:8880/techui.json')
    main_loop.Start(1)
    result = json.loads(response.ReturnResponseBody())
    self.assertNotEqual(result, None)
    self.assertEqual(result, fake_data)

  def testLoadJson(self):
    dne = '/tmp/does_not_exist'
    try:
      os.remove(dne)
    except OSError:
      pass
    result = diagui.main.LoadJson(dne)
    self.assertEqual(result, {})

    jsonfile = '/tmp/json'
    test_dict = {'11:22:33:44:55:66': 1, '11:22:33:44:55:67': 2}
    tr.helpers.WriteFileAtomic(jsonfile, json.dumps(test_dict))
    result = diagui.main.LoadJson(jsonfile)
    self.assertEqual(result, test_dict)
    try:
      os.remove(jsonfile)
    except OSError:
      pass

  def testUpdateMocaDict(self):
    techui = diagui.main.TechUI(None)
    techui.root = dm_root.DeviceModelRoot(None, 'fakecpe', None)
    interface_list = techui.root.Device.MoCA.InterfaceList
    snr = {}
    bitloading = {}
    corrected_cw = {}
    uncorrected_cw = {}
    nbas = {}
    for unused_i, inter in interface_list.iteritems():
      for unused_j, dev in inter.AssociatedDeviceList.iteritems():
        snr[dev.MACAddress] = dev.X_CATAWAMPUS_ORG_RxSNR_dB
        bitloading[dev.MACAddress] = dev.X_CATAWAMPUS_ORG_RxBitloading
        nbas[dev.MACAddress] = dev.X_CATAWAMPUS_ORG_RxNBAS
        corrected = (dev.X_CATAWAMPUS_ORG_RxPrimaryCwCorrected +
                     dev.X_CATAWAMPUS_ORG_RxSecondaryCwCorrected)
        uncorrected = (dev.X_CATAWAMPUS_ORG_RxPrimaryCwUncorrected +
                       dev.X_CATAWAMPUS_ORG_RxSecondaryCwUncorrected)
        no_errors = (dev.X_CATAWAMPUS_ORG_RxPrimaryCwNoErrors +
                     dev.X_CATAWAMPUS_ORG_RxSecondaryCwNoErrors)
        total = corrected + uncorrected + no_errors
        if total > 0:
          corrected_cw[dev.MACAddress] = corrected/total
          uncorrected_cw[dev.MACAddress] = uncorrected/total
        else:
          corrected_cw[dev.MACAddress] = 0
          uncorrected_cw[dev.MACAddress] = 0
    techui.UpdateMocaDict()
    self.assertEqual(snr, techui.data['moca_signal_strength'])
    self.assertEqual(bitloading, techui.data['moca_bitloading'])
    self.assertEqual(corrected_cw,
                     techui.data['moca_corrected_codewords'])
    self.assertEqual(uncorrected_cw,
                     techui.data['moca_uncorrected_codewords'])
    self.assertEqual(nbas, techui.data['moca_nbas'])

if __name__ == '__main__':
  unittest.main()
