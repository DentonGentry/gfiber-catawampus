#!/usr/bin/python
#
# Copyright 2012 Google Inc. All Rights Reserved.
#
# unittest requires method names starting in 'test'
#pylint: disable-msg=C6409

"""Unit tests for brcmwifi.py implementation."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import fix_path

import brcmwifi
import os
import stat
import tempfile
import unittest


class BrcmWifiTest(unittest.TestCase):
  def setUp(self):
    self.old_WL_EXE = brcmwifi.WL_EXE
    brcmwifi.WL_EXE = "testdata/brcmwifi/wlcounters"
    self.files_to_remove = list()

  def tearDown(self):
    brcmwifi.WL_EXE = self.old_WL_EXE
    for file in self.files_to_remove:
      os.remove(file)

  def MakeTestScript(self):
    """Create a script in /tmp, with an output file."""
    scriptfile = tempfile.NamedTemporaryFile(mode="r+", delete=False)
    os.chmod(scriptfile.name, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
    outfile = tempfile.NamedTemporaryFile(delete=False)
    text = "#!/bin/sh\necho $* > {0}".format(outfile.name)
    scriptfile.write(text)
    scriptfile.close()  # Linux won't run it if text file is busy
    self.files_to_remove.append(scriptfile.name)
    self.files_to_remove.append(outfile.name)
    return (scriptfile, outfile)

  def testValidateExports(self):
    bw = brcmwifi.BrcmWifiWlanConfiguration()
    brcmwifi.WL_EXE = "testdata/brcmwifi/wlempty"
    bw.ValidateExports()

  def testCounters(self):
    brcmwifi.WL_EXE = "testdata/brcmwifi/wlcounters"
    counters = brcmwifi._GetWlCounters()
    self.assertEqual(counters['rxrtsocast'], '93')
    self.assertEqual(counters['d11_txfrmsnt'], '0')
    self.assertEqual(counters['txfunfl'], ['59', '60', '61', '62', '63', '64'])

  def testStatus(self):
    brcmwifi.WL_EXE = "testdata/brcmwifi/wlbssup"
    bw = brcmwifi.BrcmWifiWlanConfiguration()
    self.assertEqual(bw.Status, "Up")
    brcmwifi.WL_EXE = "testdata/brcmwifi/wlbssdown"
    self.assertEqual(bw.Status, "Disabled")
    brcmwifi.WL_EXE = "testdata/brcmwifi/wlbsserr"
    self.assertEqual(bw.Status, "Error")

  def testChannel(self):
    brcmwifi.WL_EXE = "testdata/brcmwifi/wlchannel"
    bw = brcmwifi.BrcmWifiWlanConfiguration()
    self.assertEqual(bw.Channel, 1)

  def testValidateChannel(self):
    brcmwifi.WL_EXE = "testdata/brcmwifi/wlchannel"
    self.assertTrue(brcmwifi._ValidateChannel("1"))
    self.assertTrue(brcmwifi._ValidateChannel("11"))
    self.assertTrue(brcmwifi._ValidateChannel("13"))
    self.assertTrue(brcmwifi._ValidateChannel("36"))
    self.assertTrue(brcmwifi._ValidateChannel("140"))
    self.assertTrue(brcmwifi._ValidateChannel("149"))
    self.assertTrue(brcmwifi._ValidateChannel("165"))
    self.assertFalse(brcmwifi._ValidateChannel("166"))
    self.assertFalse(brcmwifi._ValidateChannel("14"))
    self.assertFalse(brcmwifi._ValidateChannel("0"))
    self.assertFalse(brcmwifi._ValidateChannel("20"))

  def testSetChannel(self):
    (script, out) = self.MakeTestScript()
    brcmwifi.WL_EXE = script.name
    brcmwifi._SetChannel(None, "11")
    output = out.read()
    out.close()
    self.assertEqual(output, "channel 11\n")

  def testOutputContiguousRanges(self):
    self.assertEqual(brcmwifi._OutputContiguousRanges([1,2,3,4,5]), "1-5")
    self.assertEqual(brcmwifi._OutputContiguousRanges([1,2,3,5]), "1-3,5")
    self.assertEqual(brcmwifi._OutputContiguousRanges([1,2,3,5,6,7]), "1-3,5-7")
    self.assertEqual(brcmwifi._OutputContiguousRanges([1,2,3,5,7,8,9]),
                     "1-3,5,7-9")
    self.assertEqual(brcmwifi._OutputContiguousRanges([1,3,5,7,9]), "1,3,5,7,9")

  def testPossibleChannels(self):
    brcmwifi.WL_EXE = "testdata/brcmwifi/wlchannels"
    bw = brcmwifi.BrcmWifiWlanConfiguration()
    self.assertEqual(bw.PossibleChannels,
                     "1-11,36,40,44,48,52,56,60,64,100,104,108,112,116,120,124,128,132,136,140,149,153,157,161,165")

  def testSSID(self):
    brcmwifi.WL_EXE = "testdata/brcmwifi/wlssid"
    bw = brcmwifi.BrcmWifiWlanConfiguration()
    self.assertEqual(bw.SSID, 'MySSID')
    brcmwifi.WL_EXE = "testdata/brcmwifi/wlssidempty"
    self.assertEqual(bw.SSID, '')

  def testValidateSSID(self):
    self.assertTrue(brcmwifi._ValidateSSID(r'myssid'))
    self.assertFalse(brcmwifi._ValidateSSID(r'myssid?'))
    self.assertFalse(brcmwifi._ValidateSSID(r'myssid"'))
    self.assertFalse(brcmwifi._ValidateSSID(r'myssid$'))
    self.assertFalse(brcmwifi._ValidateSSID(r'myssi\d'))
    self.assertFalse(brcmwifi._ValidateSSID(r'myssid['))
    self.assertFalse(brcmwifi._ValidateSSID(r'myssid]'))
    self.assertFalse(brcmwifi._ValidateSSID(r'myssid+'))
    self.assertFalse(brcmwifi._ValidateSSID(r'!myssid'))
    self.assertFalse(brcmwifi._ValidateSSID(r'#myssid'))
    self.assertFalse(brcmwifi._ValidateSSID(r';myssid'))
    self.assertTrue(brcmwifi._ValidateSSID(r'myssid!'))
    self.assertTrue(brcmwifi._ValidateSSID(r'myssid#'))
    self.assertTrue(brcmwifi._ValidateSSID(r'myssid;'))

  def testSetSSID(self):
    (script, out) = self.MakeTestScript()
    brcmwifi.WL_EXE = script.name
    bw = brcmwifi.BrcmWifiWlanConfiguration()
    bw.SSID = "myssid"
    output = out.read()
    out.close()
    self.assertEqual(output, "ssid myssid\n")

  def testBSSID(self):
    brcmwifi.WL_EXE = "testdata/brcmwifi/wlbssid"
    bw = brcmwifi.BrcmWifiWlanConfiguration()
    self.assertEqual(bw.BSSID, '01:23:45:67:89:ab')
    brcmwifi.WL_EXE = "testdata/brcmwifi/wlempty"
    self.assertEqual(bw.BSSID, '00:00:00:00:00:00')

  def testValidateBSSID(self):
    self.assertTrue(brcmwifi._ValidateBSSID("01:23:45:67:89:ab"))
    self.assertFalse(brcmwifi._ValidateBSSID("This is not a BSSID."))
    self.assertFalse(brcmwifi._ValidateBSSID("00:00:00:00:00:00"))
    self.assertFalse(brcmwifi._ValidateBSSID("ff:ff:ff:ff:ff:ff"))

  def testSetBSSID(self):
    (script, out) = self.MakeTestScript()
    brcmwifi.WL_EXE = script.name
    bw = brcmwifi.BrcmWifiWlanConfiguration()
    bw.BSSID = "00:99:aa:bb:cc:dd"
    output = out.read()
    out.close()
    self.assertEqual(output, "bssid 00:99:aa:bb:cc:dd\n")

  def testRegulatoryDomain(self):
    brcmwifi.WL_EXE = "testdata/brcmwifi/wlcountry.us"
    bw = brcmwifi.BrcmWifiWlanConfiguration()
    self.assertEqual(bw.RegulatoryDomain, "US")
    brcmwifi.WL_EXE = "testdata/brcmwifi/wlcountry.jp"
    self.assertEqual(bw.RegulatoryDomain, "JP")

  def testValidateRegulatoryDomain(self):
    brcmwifi.WL_EXE = "testdata/brcmwifi/wlcountrylist"
    self.assertTrue(brcmwifi._ValidateRegulatoryDomain("US"))
    self.assertTrue(brcmwifi._ValidateRegulatoryDomain("JP"))
    self.assertTrue(brcmwifi._ValidateRegulatoryDomain("SA"))
    self.assertFalse(brcmwifi._ValidateRegulatoryDomain("ZZ"))
    self.assertFalse(brcmwifi._ValidateRegulatoryDomain(""))

  def testSetRegulatoryDomain(self):
    bw = brcmwifi.BrcmWifiWlanConfiguration()
    (script, out) = self.MakeTestScript()
    brcmwifi.WL_EXE = script.name
    bw.RegulatoryDomain = "US"
    output = out.read()
    out.close()
    self.assertEqual(output, "country US\n")

  def testBasicRateSet(self):
    brcmwifi.WL_EXE = "testdata/brcmwifi/wlrateset"
    bw = brcmwifi.BrcmWifiWlanConfiguration()
    self.assertEqual(bw.BasicDataTransmitRates, "1,2,5.5,11")
    brcmwifi.WL_EXE = "testdata/brcmwifi/wlrateset2"
    self.assertEqual(bw.BasicDataTransmitRates, "1,2,5.5,11,16.445")

  def testOperationalRateSet(self):
    brcmwifi.WL_EXE = "testdata/brcmwifi/wlrateset"
    bw = brcmwifi.BrcmWifiWlanConfiguration()
    self.assertEqual(bw.OperationalDataTransmitRates,
                     "1,2,5.5,6,9,11,12,18,24,36,48,54")
    brcmwifi.WL_EXE = "testdata/brcmwifi/wlrateset2"
    self.assertEqual(bw.OperationalDataTransmitRates, "1,2,5.5,7.5,11,16.445")

  def testTransmitPower(self):
    brcmwifi.WL_EXE = "testdata/brcmwifi/wlpwrpercent"
    bw = brcmwifi.BrcmWifiWlanConfiguration()
    self.assertEqual(bw.TransmitPower, "25")

  def testValidateTransmitPower(self):
    self.assertTrue(brcmwifi._ValidateTransmitPower("100"))
    self.assertTrue(brcmwifi._ValidateTransmitPower("50"))
    self.assertTrue(brcmwifi._ValidateTransmitPower("1"))
    self.assertFalse(brcmwifi._ValidateTransmitPower("101"))
    self.assertFalse(brcmwifi._ValidateTransmitPower("foo"))

  def testSetTransmitPower(self):
    bw = brcmwifi.BrcmWifiWlanConfiguration()
    (script, out) = self.MakeTestScript()
    brcmwifi.WL_EXE = script.name
    bw.TransmitPower = "77"
    output = out.read()
    out.close()
    self.assertEqual(output, "pwr_percent 77\n")

  def testTransmitPowerSupported(self):
    bw = brcmwifi.BrcmWifiWlanConfiguration()
    self.assertEqual(bw.TransmitPowerSupported, "1-100")

  def testAutoRateFallBackEnabled(self):
    bw = brcmwifi.BrcmWifiWlanConfiguration()
    brcmwifi.WL_EXE = "testdata/brcmwifi/wlinterference0"
    self.assertFalse(bw.AutoRateFallBackEnabled)
    brcmwifi.WL_EXE = "testdata/brcmwifi/wlinterference1"
    self.assertFalse(bw.AutoRateFallBackEnabled)
    brcmwifi.WL_EXE = "testdata/brcmwifi/wlinterference2"
    self.assertFalse(bw.AutoRateFallBackEnabled)
    brcmwifi.WL_EXE = "testdata/brcmwifi/wlinterference3"
    self.assertTrue(bw.AutoRateFallBackEnabled)
    brcmwifi.WL_EXE = "testdata/brcmwifi/wlinterference4"
    self.assertTrue(bw.AutoRateFallBackEnabled)

  def testSetAutoRateFallBackEnabled(self):
    bw = brcmwifi.BrcmWifiWlanConfiguration()
    (script, out) = self.MakeTestScript()
    brcmwifi.WL_EXE = script.name
    bw.AutoRateFallBackEnabled = "True"
    output = out.read()
    out.close()
    self.assertEqual(output, "interference 4\n")
    (script, out) = self.MakeTestScript()
    brcmwifi.WL_EXE = script.name
    bw.AutoRateFallBackEnabled = "False"
    output = out.read()
    out.close()
    self.assertEqual(output, "interference 3\n")

  def testValidateAutoRateFallBackEnabled(self):
    self.assertTrue(brcmwifi._ValidateAutoRateFallBackEnabled("True"))
    self.assertTrue(brcmwifi._ValidateAutoRateFallBackEnabled("False"))
    self.assertTrue(brcmwifi._ValidateAutoRateFallBackEnabled("0"))
    self.assertTrue(brcmwifi._ValidateAutoRateFallBackEnabled("1"))
    self.assertFalse(brcmwifi._ValidateAutoRateFallBackEnabled("foo"))

  def testSSIDAdvertisementEnabled(self):
    bw = brcmwifi.BrcmWifiWlanConfiguration()
    brcmwifi.WL_EXE = "testdata/brcmwifi/wlclosed0"
    self.assertTrue(bw.SSIDAdvertisementEnabled)
    brcmwifi.WL_EXE = "testdata/brcmwifi/wlclosed1"
    self.assertFalse(bw.SSIDAdvertisementEnabled)

  def testValidateSSIDAdvertisementEnabled(self):
    self.assertTrue(brcmwifi._ValidateSSIDAdvertisementEnabled("True"))
    self.assertTrue(brcmwifi._ValidateSSIDAdvertisementEnabled("False"))
    self.assertTrue(brcmwifi._ValidateSSIDAdvertisementEnabled("0"))
    self.assertTrue(brcmwifi._ValidateSSIDAdvertisementEnabled("1"))
    self.assertFalse(brcmwifi._ValidateSSIDAdvertisementEnabled("foo"))

  def testSetSSIDAdvertisementEnabled(self):
    bw = brcmwifi.BrcmWifiWlanConfiguration()
    (script, out) = self.MakeTestScript()
    brcmwifi.WL_EXE = script.name
    bw.SSIDAdvertisementEnabled = "True"
    output = out.read()
    out.close()
    self.assertEqual(output, "closed 0\n")
    (script, out) = self.MakeTestScript()
    brcmwifi.WL_EXE = script.name
    bw.SSIDAdvertisementEnabled = "False"
    output = out.read()
    out.close()
    self.assertEqual(output, "closed 1\n")

  def testRadioEnabled(self):
    bw = brcmwifi.BrcmWifiWlanConfiguration()
    brcmwifi.WL_EXE = "testdata/brcmwifi/wlradiooff"
    self.assertFalse(bw.RadioEnabled)
    brcmwifi.WL_EXE = "testdata/brcmwifi/wlradioon"
    self.assertTrue(bw.RadioEnabled)

  def testValidateRadioEnabled(self):
    self.assertTrue(brcmwifi._ValidateRadioEnabled("True"))
    self.assertTrue(brcmwifi._ValidateRadioEnabled("False"))
    self.assertTrue(brcmwifi._ValidateRadioEnabled("0"))
    self.assertTrue(brcmwifi._ValidateRadioEnabled("1"))
    self.assertFalse(brcmwifi._ValidateRadioEnabled("foo"))

  def testSetRadioEnabled(self):
    bw = brcmwifi.BrcmWifiWlanConfiguration()
    (script, out) = self.MakeTestScript()
    brcmwifi.WL_EXE = script.name
    bw.RadioEnabled = "True"
    output = out.read()
    out.close()
    self.assertEqual(output, "radio on\n")
    (script, out) = self.MakeTestScript()
    brcmwifi.WL_EXE = script.name
    bw.RadioEnabled = "False"
    output = out.read()
    out.close()
    self.assertEqual(output, "radio off\n")


if __name__ == '__main__':
  unittest.main()
