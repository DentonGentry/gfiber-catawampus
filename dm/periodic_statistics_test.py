#!/usr/bin/python
#
# Copyright 2012 Google Inc. All Rights Reserved.
#
# unittest requires method names starting in 'test'
#pylint: disable-msg=C6409

"""Unit tests for periodic_statistics.py."""

__author__ = 'jnewlin@google.com (John Newlin)'

import datetime
import mox
import time
import unittest

import google3
import periodic_statistics
import tornado.ioloop
import tr.core
import tr.http


class FakeWLAN(tr.core.Exporter):
  def __init__(self):
    tr.core.Exporter.__init__(self)
    self.Export(['TotalBytesSent'])
    self.TotalBytesSent = 100


class PeriodicStatisticsTest(unittest.TestCase):
  def setUp(self):
    self.ps = periodic_statistics.PeriodicStatistics()

  def tearDown(self):
    pass

  def testValidateExports(self):
    self.ps.ValidateExports()
    # Add some samples sets and check again.
    self.ps.AddExportObject('SampleSet', '0')
    self.ps.AddExportObject('SampleSet', '1')
    self.assertTrue(0 in self.ps.sample_sets)
    self.assertTrue(1 in self.ps.sample_sets)
    self.ps.sample_sets[0].AddExportObject('Parameter', '0')
    self.ps.sample_sets[0].AddExportObject('Parameter', '1')
    self.ps.sample_sets[1].AddExportObject('Parameter', '0')
    self.ps.sample_sets[1].AddExportObject('Parameter', '1')
    self.assertTrue(0 in self.ps.sample_sets[0]._parameter_list)
    self.assertTrue(1 in self.ps.sample_sets[0]._parameter_list)
    self.assertTrue(0 in self.ps.sample_sets[1]._parameter_list)
    self.assertTrue(1 in self.ps.sample_sets[1]._parameter_list)
    self.ps.ValidateExports()

  def testSetCpeRoot(self):
    fake_cpe = object()
    fake_root = object()
    self.ps.SetCpe(fake_cpe)
    self.ps.SetRoot(fake_root)
    self.assertEqual(fake_cpe, self.ps._cpe)
    self.assertEqual(fake_root, self.ps._root)

  def testFinishedSampling(self):
    sample_set = periodic_statistics.PeriodicStatistics.SampleSet()
    self.assertTrue(sample_set.FinishedSampling())

  def testCollectSample(self):
    obj_name = 'InternetGatewayDevice.LANDevice.1.WLANConfiguration.1.'
    obj_param = 'TotalBytesSent'
    sampled_param = periodic_statistics.PeriodicStatistics.SampleSet.Parameter()
    sampled_param.Enable = True
    sampled_param.Reference = obj_name + obj_param
    sample_set = periodic_statistics.PeriodicStatistics.SampleSet()
    m = mox.Mox()
    mock_root = m.CreateMock(tr.core.Exporter)
    fake_wlan = FakeWLAN()
    mock_root.GetExport(mox.IsA(str)).AndReturn(1000)
    m.ReplayAll()

    sample_set.SetCpeAndRoot(cpe=object(), root=mock_root)
    sample_set.SetParameter('1', sampled_param)
    sample_set.CollectSample()
    m.VerifyAll()

    # Check that the sampled_param updated it's values.
    self.assertEqual('1000', sampled_param.Values)


class SampleSetTest(unittest.TestCase):
  def setUp(self):
    self.ps = periodic_statistics.PeriodicStatistics()
    self.m = mox.Mox()
    self.mock_root = self.m.CreateMock(tr.core.Exporter)
    self.mock_cpe = self.m.CreateMock(tr.http.CPEStateMachine)
    self.ps.SetCpe(self.mock_cpe)
    self.ps.SetRoot(self.mock_root)

  def tearDown(self):
    self.m.VerifyAll()

  def testValidateExports(self):
    sample_set = periodic_statistics.PeriodicStatistics.SampleSet()
    sample_set.ValidateExports()

  def testParameters(self):
    sample_set = periodic_statistics.PeriodicStatistics.SampleSet()
    param1 = periodic_statistics.PeriodicStatistics.SampleSet.Parameter()
    sample_set.ParameterList['0'] = param1
    self.assertEqual(1, len(sample_set.ParameterList))
    for key in sample_set.ParameterList:
      self.assertEqual(key, '0')
      self.assertEqual(sample_set.ParameterList[key], param1)
    del sample_set.ParameterList['0']
    self.assertEqual(0, len(sample_set.ParameterList))

  def testReportSamples(self):
    sample_set = periodic_statistics.PeriodicStatistics.SampleSet()
    self.assertEqual(0, sample_set.ReportSamples)
    sample_set.ReportSamples = '10'
    self.assertEqual(10, sample_set.ReportSamples)

  def testSampleInterval(self):
    sample_set = periodic_statistics.PeriodicStatistics.SampleSet()
    self.ps.SampleSetList['0'] = sample_set
    self.assertTrue(sample_set.FinishedSampling())
    self.assertEqual(0, sample_set.SampleInterval)
    sample_set.SampleInterval = 10
    self.assertEqual(10, sample_set.SampleInterval)

  def testCollectSample(self):
    sample_set = periodic_statistics.PeriodicStatistics.SampleSet()
    self.ps.SampleSetList['0'] = sample_set
    start1_time = time.time()
    sample_set.CollectSample()
    end1_time = time.time()
    self.assertEqual(1, len(sample_set._sample_seconds))
    self.assertTrue(start1_time <= sample_set._sample_seconds[0])
    self.assertTrue(end1_time >= sample_set._sample_seconds[0])
    start1_time = time.time()
    sample_set.CollectSample()
    end2_time = time.time()
    self.assertEqual(2, len(sample_set._sample_seconds))
    self.assertTrue(
        sample_set._sample_seconds[0] < sample_set._sample_seconds[1])
    self.assertEqual(sample_set.SampleSeconds, '0,0')


  def testSampleTrigger(self):
    mock_ioloop = self.m.CreateMock(tornado.ioloop.IOLoop)
    self.mock_cpe.ioloop = mock_ioloop
    sample_set = periodic_statistics.PeriodicStatistics.SampleSet()
    self.ps.SampleSetList['0'] = sample_set
    mock_ioloop.add_timeout(mox.IsA(datetime.timedelta),
                            mox.IgnoreArg()).AndReturn(1)
    self.m.ReplayAll()
    sample_set.SetSampleTrigger()

  def testUpdateSampling(self):
    sample_set = periodic_statistics.PeriodicStatistics.SampleSet()
    self.m.StubOutWithMock(sample_set, 'SetSampleTrigger')
    self.m.StubOutWithMock(sample_set, 'StopSampling')

    # First call should call StopSampling
    sample_set.StopSampling()  # first call
    sample_set.StopSampling()  # Calle for Enable toggle
    sample_set.StopSampling()  # Called when ReportSamples is set
    sample_set.SetSampleTrigger()  # called when SampleInterval is set
    sample_set.StopSampling()
    self.m.ReplayAll()

    sample_set.UpdateSampling()
    sample_set.Enable = 'True'
    sample_set.ReportSamples = 100
    sample_set.SampleInterval = 100
    sample_set.Enable = 'False'

  def testFinishedSampling(self):
    sample_set = periodic_statistics.PeriodicStatistics.SampleSet()
    self.assertTrue(sample_set.FinishedSampling())
    sample_set._enable = True
    sample_set.ReportSamples = 10
    self.assertFalse(sample_set.FinishedSampling())

  def testSampleSeconds(self):
    # Insert some phone values into sample_seconds
    sample_set = periodic_statistics.PeriodicStatistics.SampleSet()
    sample_set._sample_seconds = []
    self.assertEqual('', sample_set.SampleSeconds)
    sample_set._sample_seconds.append(10.2)
    self.assertEqual('0', sample_set.SampleSeconds)
    sample_set._sample_seconds.append(11.8)
    self.assertEqual('0,2', sample_set.SampleSeconds)
    sample_set._sample_seconds.append(13.2)
    self.assertEqual(sample_set.SampleSeconds, '0,2,1')

  def testPassiveNotify(self):
    sample_set = periodic_statistics.PeriodicStatistics.SampleSet()
    self.m.StubOutWithMock(sample_set, 'ClearSamplingData')
    PARAMETER = periodic_statistics.PeriodicStatistics.SampleSet.Parameter
    mock_cpe = self.m.CreateMock(tr.http.CPEStateMachine)
    mock_root = self.m.CreateMock(tr.core.Exporter)
    mock_param1 = self.m.CreateMock(PARAMETER)
    mock_param2 = self.m.CreateMock(PARAMETER)
    mock_param1.Reference = 'Fake.Param.One'
    mock_param2.Reference = 'Fake.Param.Two'
    sample_set.ClearSamplingData()
    mock_param1.CollectSample().AndReturn(100)
    mock_param2.CollectSample().AndReturn(200)
    obj_name = 'Device.PeriodicStatistics.SampleSet.0'
    param_name = obj_name + '.Status'
    mock_root.GetCanonicalName(sample_set).AndReturn(obj_name)
    mock_cpe.SetNotificationParameters([(param_name, 'Disabled')])
    self.m.ReplayAll()

    self.assertEqual({}, sample_set._parameter_list)
    sample_set._parameter_list['1'] = mock_param1
    sample_set._parameter_list['2'] = mock_param2
    sample_set.SetCpeAndRoot(cpe=mock_cpe, root=mock_root)
    self.assertEqual(0, sample_set.FetchSamples)
    sample_set.FetchSamples = 1
    self.assertEqual(1, sample_set.FetchSamples)
    sample_set.ReportSamples = 1
    sample_set.Enable = 'True'
    sample_set._attributes['Notification'] = 1
    sample_set.CollectSample()
    print "end testPassNotify"

  def testActiveNotify(self):
    sample_set = periodic_statistics.PeriodicStatistics.SampleSet()
    self.m.StubOutWithMock(sample_set, 'ClearSamplingData')
    PARAMETER = periodic_statistics.PeriodicStatistics.SampleSet.Parameter
    mock_cpe = self.m.CreateMock(tr.http.CPEStateMachine)
    mock_root = self.m.CreateMock(tr.core.Exporter)
    mock_param1 = self.m.CreateMock(PARAMETER)
    mock_param2 = self.m.CreateMock(PARAMETER)
    mock_param1.Reference = 'Fake.Param.One'
    mock_param2.Reference = 'Fake.Param.Two'
    mock_param1.CollectSample().AndReturn(100)
    mock_param2.CollectSample().AndReturn(200)
    obj_name = 'Device.PeriodicStatistics.SampleSet.0'
    param_name = obj_name + '.Status'
    sample_set.ClearSamplingData()
    mock_root.GetCanonicalName(sample_set).AndReturn(obj_name)
    mock_cpe.SetNotificationParameters([(param_name, 'Disabled')])
    mock_cpe.NewValueChangeSession()
    self.m.ReplayAll()

    self.assertEqual({}, sample_set._parameter_list)
    sample_set._parameter_list['1'] = mock_param1
    sample_set._parameter_list['2'] = mock_param2
    sample_set.SetCpeAndRoot(cpe=mock_cpe, root=mock_root)
    self.assertEqual(0, sample_set.FetchSamples)
    sample_set.FetchSamples = 1
    self.assertEqual(1, sample_set.FetchSamples)
    sample_set.ReportSamples = 1
    sample_set.Enable = 'True'
    sample_set._attributes['Notification'] = 2
    sample_set.CollectSample()

  def testClearSamplingData(self):
    sample_set = periodic_statistics.PeriodicStatistics.SampleSet()
    param1 = periodic_statistics.PeriodicStatistics.SampleSet.Parameter()
    param2 = periodic_statistics.PeriodicStatistics.SampleSet.Parameter()
    sample_set.ClearSamplingData()
    sample_set.ParameterList['0'] = param1
    sample_set.ParameterList['1'] = param2
    self.assertEqual(2, len(sample_set._parameter_list))
    sample_set.ClearSamplingData()
    # put in some fake data
    sample_set._sample_seconds = [1, 2, 3]
    sample_set._fetch_samples = 10
    sample_set._report_samples = 10
    param1._values = ['1', '2', '3']
    param1._sample_seconds = [5, 6, 7]
    param2._values = ['5', '6', '7']
    param2._sample_seconds = [8, 9, 10]
    sample_set.ClearSamplingData()
    self.assertEqual(0, len(sample_set._sample_seconds))
    self.assertEqual(0, len(param1._sample_seconds))
    self.assertEqual(0, len(param2._sample_seconds))
    self.assertEqual(0, len(param1._values))
    self.assertEqual(0, len(param2._values))


if __name__ == '__main__':
  unittest.main()
