#!/usr/bin/python
#
# Copyright 2012 Google Inc. All Rights Reserved.
#
# unittest requires method names starting in 'test'
#pylint: disable-msg=C6409

"""Unit tests for brcmwifi.py implementation."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import os
import stat
import tempfile
import unittest

import google3
import brcmwifi
import netdev


class BrcmWifiTest(unittest.TestCase):
  def setUp(self):
    self.old_WL_EXE = brcmwifi.WL_EXE
    self.old_PROC_NET_DEV = netdev.PROC_NET_DEV
    self.files_to_remove = list()

  def tearDown(self):
    brcmwifi.WL_EXE = self.old_WL_EXE
    netdev.PROC_NET_DEV = self.old_PROC_NET_DEV
    for f in self.files_to_remove:
      os.remove(f)

  def MakeTestScript(self):
    """Create a script in /tmp, with an output file."""
    scriptfile = tempfile.NamedTemporaryFile(mode='r+', delete=False)
    os.chmod(scriptfile.name, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
    outfile = tempfile.NamedTemporaryFile(delete=False)
    text = '#!/bin/sh\necho $* >> {0}'.format(outfile.name)
    scriptfile.write(text)
    scriptfile.close()  # Linux won't run it if text file is busy
    self.files_to_remove.append(scriptfile.name)
    self.files_to_remove.append(outfile.name)
    return (scriptfile, outfile)

  def RmFromList(self, l, item):
    try:
      l.remove(item)
      return True
    except ValueError:
      return False

  def VerifyCommonWlCommands(self, cmd, rmwep=4, wsec=0, primary_key=1,
                             wepstatus='off'):
    # Verify the number of "rmwep #" commands, and remove them.
    l = [x for x in cmd.split('\n') if x]  # Suppress blank lines
    for i in range(0, rmwep):
      self.assertTrue(self.RmFromList(l, 'rmwep %d' % i))
    self.assertTrue(self.RmFromList(l, 'wsec %d' % wsec))
    self.assertTrue(self.RmFromList(l, 'primary_key %d' % primary_key))
    self.assertTrue(self.RmFromList(l, 'wepstatus %s' % wepstatus))
    self.assertTrue(len(l) >= 7)
    self.assertEqual(l[0], 'down')
    self.assertEqual(l[1], 'radio off')
    self.assertEqual(l[2], 'bss down')
    self.assertEqual(l[3], 'radio on')
    self.assertEqual(l[4], 'up')
    self.assertEqual(l[5], 'ap 1')
    self.assertEqual(l[6], 'infra 1')
    return l[7:]

  def testValidateExports(self):
    netdev.PROC_NET_DEV = 'testdata/brcmwifi/proc_net_dev'
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlempty'
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    bw.ValidateExports()
    stats = brcmwifi.BrcmWlanConfigurationStats('wifi0')
    stats.ValidateExports()

  def testCounters(self):
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlcounters'
    counters = brcmwifi._GetWlCounters()
    self.assertEqual(counters['rxrtsocast'], '93')
    self.assertEqual(counters['d11_txfrmsnt'], '0')
    self.assertEqual(counters['txfunfl'], ['59', '60', '61', '62', '63', '64'])

  def testStatus(self):
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlbssup'
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    self.assertEqual(bw.Status, 'Up')
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlbssdown'
    self.assertEqual(bw.Status, 'Disabled')
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlbsserr'
    self.assertEqual(bw.Status, 'Error')

  def testChannel(self):
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlchannel'
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    self.assertEqual(bw.Channel, 1)

  def testValidateChannel(self):
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlchannel'
    self.assertTrue(brcmwifi._ValidateChannel('1'))
    self.assertTrue(brcmwifi._ValidateChannel('11'))
    self.assertTrue(brcmwifi._ValidateChannel('13'))
    self.assertTrue(brcmwifi._ValidateChannel('36'))
    self.assertTrue(brcmwifi._ValidateChannel('140'))
    self.assertTrue(brcmwifi._ValidateChannel('149'))
    self.assertTrue(brcmwifi._ValidateChannel('165'))
    self.assertFalse(brcmwifi._ValidateChannel('166'))
    self.assertFalse(brcmwifi._ValidateChannel('14'))
    self.assertFalse(brcmwifi._ValidateChannel('0'))
    self.assertFalse(brcmwifi._ValidateChannel('20'))

  def testSetChannel(self):
    (script, out) = self.MakeTestScript()
    brcmwifi.WL_EXE = script.name
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    bw.Enable = 'True'
    bw.RadioEnabled = 'True'
    out.truncate()
    bw.Channel = '11'
    output = out.read()
    out.close()
    outlist = self.VerifyCommonWlCommands(output)
    self.assertTrue(self.RmFromList(outlist, 'channel 11'))
    self.assertFalse(outlist)

  def testPossibleChannels(self):
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlchannels'
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    self.assertEqual(bw.PossibleChannels,
                     '1-11,36,40,44,48,52,56,60,64,100,104,108,112,116,120,124,'
                     '128,132,136,140,149,153,157,161,165')

  def testSSID(self):
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlssid'
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    self.assertEqual(bw.SSID, 'MySSID')
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlssidempty'
    self.assertEqual(bw.SSID, '')

  def testValidateSSID(self):
    self.assertTrue(brcmwifi._ValidateSSID(r'myssid'))
    self.assertTrue(brcmwifi._ValidateSSID(r'my ssid'))
    self.assertFalse(brcmwifi._ValidateSSID(
        r'myssidiswaaaaaaaaaaaaaaaaaytoolongtovalidate'))

  def testSetSSID(self):
    (script, out) = self.MakeTestScript()
    brcmwifi.WL_EXE = script.name
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    bw.Enable = 'True'
    bw.RadioEnabled = 'True'
    out.truncate()
    bw.SSID = 'myssid'
    output = out.read()
    out.close()
    outlist = self.VerifyCommonWlCommands(output)
    self.assertTrue(self.RmFromList(outlist, 'ssid myssid'))
    self.assertTrue(self.RmFromList(outlist, 'bss up'))
    self.assertFalse(outlist)

  def testBSSID(self):
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlbssid'
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    self.assertEqual(bw.BSSID, '01:23:45:67:89:ab')
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlempty'
    self.assertEqual(bw.BSSID, '00:00:00:00:00:00')

  def testValidateBSSID(self):
    self.assertTrue(brcmwifi._ValidateBSSID('01:23:45:67:89:ab'))
    self.assertFalse(brcmwifi._ValidateBSSID('This is not a BSSID.'))
    self.assertFalse(brcmwifi._ValidateBSSID('00:00:00:00:00:00'))
    self.assertFalse(brcmwifi._ValidateBSSID('ff:ff:ff:ff:ff:ff'))

  def testSetBSSID(self):
    (script, out) = self.MakeTestScript()
    brcmwifi.WL_EXE = script.name
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    bw.Enable = 'True'
    bw.RadioEnabled = 'True'
    out.truncate()
    bw.BSSID = '00:99:aa:bb:cc:dd'
    output = out.read()
    out.close()
    outlist = self.VerifyCommonWlCommands(output)
    self.assertTrue(self.RmFromList(outlist, 'bssid 00:99:aa:bb:cc:dd'))
    self.assertFalse(outlist)

  def testRegulatoryDomain(self):
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlcountry.us'
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    self.assertEqual(bw.RegulatoryDomain, 'US')
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlcountry.jp'
    self.assertEqual(bw.RegulatoryDomain, 'JP')

  def testValidateRegulatoryDomain(self):
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlcountrylist'
    self.assertTrue(brcmwifi._ValidateRegulatoryDomain('US'))
    self.assertTrue(brcmwifi._ValidateRegulatoryDomain('JP'))
    self.assertTrue(brcmwifi._ValidateRegulatoryDomain('SA'))
    self.assertFalse(brcmwifi._ValidateRegulatoryDomain('ZZ'))
    self.assertFalse(brcmwifi._ValidateRegulatoryDomain(''))

  def testSetRegulatoryDomain(self):
    (script, out) = self.MakeTestScript()
    brcmwifi.WL_EXE = script.name
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    bw.Enable = 'True'
    bw.RadioEnabled = 'True'
    out.truncate()
    bw.RegulatoryDomain = 'US'
    output = out.read()
    out.close()
    outlist = self.VerifyCommonWlCommands(output)
    self.assertTrue(self.RmFromList(outlist, 'country US'))
    self.assertFalse(outlist)

  def testBasicRateSet(self):
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlrateset'
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    self.assertEqual(bw.BasicDataTransmitRates, '1,2,5.5,11')
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlrateset2'
    self.assertEqual(bw.BasicDataTransmitRates, '1,2,5.5,11,16.445')

  def testOperationalRateSet(self):
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlrateset'
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    self.assertEqual(bw.OperationalDataTransmitRates,
                     '1,2,5.5,6,9,11,12,18,24,36,48,54')
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlrateset2'
    self.assertEqual(bw.OperationalDataTransmitRates, '1,2,5.5,7.5,11,16.445')

  def testTransmitPower(self):
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlpwrpercent'
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    self.assertEqual(bw.TransmitPower, '25')

  def testValidateTransmitPower(self):
    self.assertTrue(brcmwifi._ValidateTransmitPower('100'))
    self.assertTrue(brcmwifi._ValidateTransmitPower('50'))
    self.assertTrue(brcmwifi._ValidateTransmitPower('1'))
    self.assertFalse(brcmwifi._ValidateTransmitPower('101'))
    self.assertFalse(brcmwifi._ValidateTransmitPower('foo'))

  def testSetTransmitPower(self):
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    (script, out) = self.MakeTestScript()
    brcmwifi.WL_EXE = script.name
    bw.Enable = 'True'
    bw.RadioEnabled = 'True'
    out.truncate()
    bw.TransmitPower = '77'
    output = out.read()
    out.close()
    outlist = self.VerifyCommonWlCommands(output)
    self.assertTrue(self.RmFromList(outlist, 'pwr_percent 77'))
    self.assertFalse(outlist)

  def testTransmitPowerSupported(self):
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    self.assertEqual(bw.TransmitPowerSupported, '1-100')

  def testAutoRateFallBackEnabled(self):
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlinterference0'
    self.assertFalse(bw.AutoRateFallBackEnabled)
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlinterference1'
    self.assertFalse(bw.AutoRateFallBackEnabled)
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlinterference2'
    self.assertFalse(bw.AutoRateFallBackEnabled)
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlinterference3'
    self.assertTrue(bw.AutoRateFallBackEnabled)
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlinterference4'
    self.assertTrue(bw.AutoRateFallBackEnabled)

  def testSetAutoRateFallBackEnabled(self):
    (script, out) = self.MakeTestScript()
    brcmwifi.WL_EXE = script.name
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    bw.Enable = 'True'
    bw.RadioEnabled = 'True'
    out.truncate()

    bw.AutoRateFallBackEnabled = 'True'
    output = out.read()
    outlist = self.VerifyCommonWlCommands(output)
    self.assertTrue(self.RmFromList(outlist, 'interference 4'))
    self.assertFalse(outlist)
    out.truncate()
    bw.AutoRateFallBackEnabled = 'False'
    output = out.read()
    outlist = self.VerifyCommonWlCommands(output)
    out.close()
    self.assertTrue(self.RmFromList(outlist, 'interference 3'))
    self.assertFalse(outlist)

  def testValidateAutoRateFallBackEnabled(self):
    self.assertTrue(brcmwifi._ValidateAutoRateFallBackEnabled('True'))
    self.assertTrue(brcmwifi._ValidateAutoRateFallBackEnabled('False'))
    self.assertTrue(brcmwifi._ValidateAutoRateFallBackEnabled('0'))
    self.assertTrue(brcmwifi._ValidateAutoRateFallBackEnabled('1'))
    self.assertFalse(brcmwifi._ValidateAutoRateFallBackEnabled('foo'))

  def testSSIDAdvertisementEnabled(self):
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlclosed0'
    self.assertTrue(bw.SSIDAdvertisementEnabled)
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlclosed1'
    self.assertFalse(bw.SSIDAdvertisementEnabled)

  def testValidateSSIDAdvertisementEnabled(self):
    self.assertTrue(brcmwifi._ValidateSSIDAdvertisementEnabled('True'))
    self.assertTrue(brcmwifi._ValidateSSIDAdvertisementEnabled('False'))
    self.assertTrue(brcmwifi._ValidateSSIDAdvertisementEnabled('0'))
    self.assertTrue(brcmwifi._ValidateSSIDAdvertisementEnabled('1'))
    self.assertFalse(brcmwifi._ValidateSSIDAdvertisementEnabled('foo'))

  def testSetSSIDAdvertisementEnabled(self):
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    (script, out) = self.MakeTestScript()
    brcmwifi.WL_EXE = script.name
    bw.Enable = 'True'
    bw.RadioEnabled = 'True'
    out.truncate()
    bw.SSIDAdvertisementEnabled = 'True'
    output = out.read()
    outlist = self.VerifyCommonWlCommands(output)
    self.assertTrue(self.RmFromList(outlist, 'closed 0'))
    self.assertFalse(outlist)
    out.truncate()
    bw.SSIDAdvertisementEnabled = 'False'
    output = out.read()
    outlist = self.VerifyCommonWlCommands(output)
    out.close()
    self.assertTrue(self.RmFromList(outlist, 'closed 1'))
    self.assertFalse(outlist)

  def testRadioEnabled(self):
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlradiooff'
    self.assertFalse(bw.RadioEnabled)
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlradioon'
    self.assertTrue(bw.RadioEnabled)

  def testValidateRadioEnabled(self):
    self.assertTrue(brcmwifi._ValidateRadioEnabled('True'))
    self.assertTrue(brcmwifi._ValidateRadioEnabled('False'))
    self.assertTrue(brcmwifi._ValidateRadioEnabled('0'))
    self.assertTrue(brcmwifi._ValidateRadioEnabled('1'))
    self.assertFalse(brcmwifi._ValidateRadioEnabled('foo'))

  def testSetRadioEnabled(self):
    (script, out) = self.MakeTestScript()
    brcmwifi.WL_EXE = script.name
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    bw.Enable = 'True'
    out.truncate()
    bw.RadioEnabled = 'True'
    output = out.read()
    outlist = self.VerifyCommonWlCommands(output)
    self.assertFalse(outlist)
    out.truncate()
    bw.RadioEnabled = 'False'
    output = out.read()
    out.close()
    self.assertEqual(output, 'down\nradio off\nbss down\n')

  def testNoEnable(self):
    (script, out) = self.MakeTestScript()
    brcmwifi.WL_EXE = script.name
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    bw.Enable = 'False'
    output = out.read()
    out.close()
    self.assertEqual(output, 'down\n')
    self.assertFalse(bw.Enable)

  def testValidateEnable(self):
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    self.assertTrue(bw.ValidateEnable('True'))
    self.assertTrue(bw.ValidateEnable('False'))
    self.assertTrue(bw.ValidateEnable('0'))
    self.assertTrue(bw.ValidateEnable('1'))
    self.assertFalse(bw.ValidateEnable('foo'))

  def testEncryptionModes(self):
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlwsec0'
    self.assertEqual(bw.IEEE11iEncryptionModes, 'X_CATAWAMPUS-ORG_None')
    self.assertEqual(bw.WPAEncryptionModes, 'X_CATAWAMPUS-ORG_None')
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlwsec1'
    self.assertEqual(bw.IEEE11iEncryptionModes, 'WEPEncryption')
    self.assertEqual(bw.WPAEncryptionModes, 'WEPEncryption')
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlwsec2'
    self.assertEqual(bw.IEEE11iEncryptionModes, 'TKIPEncryption')
    self.assertEqual(bw.WPAEncryptionModes, 'TKIPEncryption')
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlwsec3'
    self.assertEqual(bw.IEEE11iEncryptionModes, 'WEPandTKIPEncryption')
    self.assertEqual(bw.WPAEncryptionModes, 'WEPandTKIPEncryption')
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlwsec4'
    self.assertEqual(bw.IEEE11iEncryptionModes, 'AESEncryption')
    self.assertEqual(bw.WPAEncryptionModes, 'AESEncryption')
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlwsec5'
    self.assertEqual(bw.IEEE11iEncryptionModes, 'WEPandAESEncryption')
    self.assertEqual(bw.WPAEncryptionModes, 'WEPandAESEncryption')
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlwsec6'
    self.assertEqual(bw.IEEE11iEncryptionModes, 'TKIPandAESEncryption')
    self.assertEqual(bw.WPAEncryptionModes, 'TKIPandAESEncryption')
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlwsec7'
    self.assertEqual(bw.IEEE11iEncryptionModes, 'WEPandTKIPandAESEncryption')
    self.assertEqual(bw.WPAEncryptionModes, 'WEPandTKIPandAESEncryption')
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlwsec15'
    self.assertEqual(bw.IEEE11iEncryptionModes, 'WEPandTKIPandAESEncryption')
    self.assertEqual(bw.WPAEncryptionModes, 'WEPandTKIPandAESEncryption')

  def testValidateBeaconType(self):
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    self.assertTrue(bw.ValidateBeaconType('None'))
    self.assertTrue(bw.ValidateBeaconType('Basic'))
    self.assertTrue(bw.ValidateBeaconType('WPA'))
    self.assertTrue(bw.ValidateBeaconType('BasicandWPA'))
    self.assertTrue(bw.ValidateBeaconType('11i'))
    self.assertTrue(bw.ValidateBeaconType('Basicand11i'))
    self.assertTrue(bw.ValidateBeaconType('WPAand11i'))
    self.assertTrue(bw.ValidateBeaconType('BasicandWPAand11i'))
    self.assertFalse(bw.ValidateBeaconType('FooFi'))

  def testSetBeaconType(self):
    (script, out) = self.MakeTestScript()
    brcmwifi.WL_EXE = script.name
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    bw.Enable = 'True'
    bw.RadioEnabled = 'True'
    bw.WPAEncryptionModes = 'TKIPEncryption'  # wsec 2
    bw.IEEE11iEncryptionModes = 'AESEncryption'  # wsec 4
    out.truncate()
    bw.BeaconType = 'None'
    output = out.read()
    outlist = self.VerifyCommonWlCommands(output, wsec=0)
    self.assertFalse(outlist)
    out.truncate()
    bw.BeaconType = 'Basic'
    output = out.read()
    outlist = self.VerifyCommonWlCommands(output, wsec=1, wepstatus='on')
    self.assertFalse(outlist)
    out.truncate()
    bw.BeaconType = 'WPA'
    output = out.read()
    outlist = self.VerifyCommonWlCommands(output, wsec=2)
    self.assertFalse(outlist)
    out.truncate()
    bw.BeaconType = '11i'
    output = out.read()
    outlist = self.VerifyCommonWlCommands(output, wsec=4)
    self.assertFalse(outlist)
    out.truncate()
    bw.BeaconType = 'BasicandWPA'
    output = out.read()
    outlist = self.VerifyCommonWlCommands(output, wsec=2, wepstatus='on')
    self.assertFalse(outlist)
    out.truncate()
    bw.BeaconType = 'Basicand11i'
    output = out.read()
    outlist = self.VerifyCommonWlCommands(output, wsec=4, wepstatus='on')
    self.assertFalse(outlist)
    out.truncate()
    bw.BeaconType = 'WPAand11i'
    output = out.read()
    outlist = self.VerifyCommonWlCommands(output, wsec=4)
    self.assertFalse(outlist)
    out.truncate()
    bw.BeaconType = 'BasicandWPAand11i'
    output = out.read()
    outlist = self.VerifyCommonWlCommands(output, wsec=4, wepstatus='on')
    self.assertFalse(outlist)
    out.truncate()

  def testStats(self):
    netdev.PROC_NET_DEV = 'testdata/brcmwifi/proc_net_dev'
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    stats = bw.Stats
    stats.ValidateExports()
    # pylint: disable-msg=E1101
    self.assertEqual(stats.BroadcastPacketsReceived, None)
    self.assertEqual(stats.BroadcastPacketsSent, None)
    self.assertEqual(stats.BytesReceived, '1')
    self.assertEqual(stats.BytesSent, '9')
    self.assertEqual(stats.DiscardPacketsReceived, '4')
    self.assertEqual(stats.DiscardPacketsSent, '11')
    self.assertEqual(stats.ErrorsReceived, '9')
    self.assertEqual(stats.ErrorsSent, '12')
    self.assertEqual(stats.MulticastPacketsReceived, '8')
    self.assertEqual(stats.MulticastPacketsSent, None)
    self.assertEqual(stats.PacketsReceived, '100')
    self.assertEqual(stats.PacketsSent, '10')
    self.assertEqual(stats.UnicastPacketsReceived, '92')
    self.assertEqual(stats.UnicastPacketsSent, '10')
    self.assertEqual(stats.UnknownProtoPacketsReceived, None)

  def testAssociatedDevice(self):
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlassociated'
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    self.assertEqual(bw.TotalAssociations, 3)
    speeds = {'a0:b0:c0:00:00:01': '1',
              'a0:b0:c0:00:00:02': '2',
              'a0:b0:c0:00:00:03': '3'}
    auth = {'a0:b0:c0:00:00:01': True,
            'a0:b0:c0:00:00:02': False,
            'a0:b0:c0:00:00:03': True}
    seen = set()
    for ad in bw.AssociatedDeviceList.values():
      ad.ValidateExports()
      mac = ad.AssociatedDeviceMACAddress.lower()
      self.assertEqual(ad.LastDataTransmitRate, speeds[mac])
      self.assertEqual(ad.AssociatedDeviceAuthenticationState, auth[mac])
      seen.add(mac)
    self.assertEqual(len(seen), 3)

  def testKeyPassphrase(self):
    netdev.PROC_NET_DEV = 'testdata/brcmwifi/proc_net_dev'
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    bw.KeyPassphrase = 'testpassword'
    self.assertEqual(bw.KeyPassphrase, bw.PreSharedKeyList[1].KeyPassphrase)


if __name__ == '__main__':
  unittest.main()
