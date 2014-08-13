#!/usr/bin/python
#
# Copyright 2012 Google Inc. All Rights Reserved.
#
# unittest requires method names starting in 'test'
# pylint: disable-msg=C6409

"""Unit tests for periodic_statistics.py."""

__author__ = 'jnewlin@google.com (John Newlin)'

import datetime
import time
import unittest
import weakref

import google3
import mox
import tornado.ioloop
import tr.core
import tr.http
import periodic_statistics


class FakeWLAN(tr.core.Exporter):
  def __init__(self):
    tr.core.Exporter.__init__(self)
    self.Export(['TotalBytesSent'])
    self.TotalBytesSent = 100


class PeriodicStatisticsTest(unittest.TestCase):
  def setUp(self):
    self.save_time_func = periodic_statistics.TIMEFUNC
    self.ps = periodic_statistics.PeriodicStatistics()
    self.m = mox.Mox()
    self.mock_root = self.m.CreateMock(tr.core.Exporter)
    self.mock_cpe = self.m.CreateMock(tr.http.CPEStateMachine)
    self.mock_ioloop = self.m.CreateMock(tornado.ioloop.IOLoop)
    self.mock_cpe.ioloop = self.mock_ioloop
    self.ps.SetCpe(self.mock_cpe)
    self.ps.SetRoot(self.mock_root)

  def tearDown(self):
    self.m.VerifyAll()
    periodic_statistics.TIMEFUNC = self.save_time_func

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

  def testDeleteSample(self):
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
    sample_sets = [weakref.ref(self.ps.sample_sets[0]),
                   weakref.ref(self.ps.sample_sets[1])]
    params = [weakref.ref(self.ps.sample_sets[0]._parameter_list[0]),
              weakref.ref(self.ps.sample_sets[0]._parameter_list[1]),
              weakref.ref(self.ps.sample_sets[1]._parameter_list[0]),
              weakref.ref(self.ps.sample_sets[1]._parameter_list[1])]
    self.ps.ValidateExports()
    self.ps.sample_sets[0].DeleteExportObject('Parameter', '1')
    self.ps.sample_sets[1].DeleteExportObject('Parameter', '0')
    self.assertIsNot(None, params[0]())
    self.assertIs(None, params[1]())
    self.assertIs(None, params[2]())
    self.assertIsNot(None, params[3]())
    self.assertTrue(0 in self.ps.sample_sets[0]._parameter_list)
    self.assertFalse(1 in self.ps.sample_sets[0]._parameter_list)
    self.assertFalse(0 in self.ps.sample_sets[1]._parameter_list)
    self.assertTrue(1 in self.ps.sample_sets[1]._parameter_list)
    self.ps.DeleteExportObject('SampleSet', '1')
    self.assertIsNot(None, sample_sets[0]())
    self.assertIs(None, sample_sets[1]())
    self.assertIsNot(None, params[0]())
    self.assertIs(None, params[1]())
    self.assertIs(None, params[2]())
    self.assertIs(None, params[3]())
    self.assertTrue(0 in self.ps.sample_sets[0]._parameter_list)
    self.assertFalse(1 in self.ps.sample_sets[0]._parameter_list)
    self.assertFalse(1 in self.ps.sample_sets)
    self.ps.ValidateExports()

  def testSetCpeRoot(self):
    fake_cpe = object()
    fake_root = object()
    self.ps.SetCpe(fake_cpe)
    self.ps.SetRoot(fake_root)
    self.assertEqual(fake_cpe, self.ps._cpe)
    self.assertEqual(fake_root, self.ps._root)

  def testCollectSample(self):
    obj_name = 'InternetGatewayDevice.LANDevice.1.WLANConfiguration.1.'
    obj_param = 'TotalBytesSent'
    sampled_param = periodic_statistics.PeriodicStatistics.SampleSet.Parameter()
    sampled_param.Enable = True
    sampled_param.Reference = obj_name + obj_param
    sample_set = periodic_statistics.PeriodicStatistics.SampleSet()
    self.mock_root.GetExport(mox.IsA(str)).AndReturn(1000)
    self.m.ReplayAll()

    sample_set.SetCpeAndRoot(cpe=self.mock_cpe, root=self.mock_root)
    sample_set.SetParameter('1', sampled_param)
    sample_set.CollectSample()

    # Check that the sampled_param updated it's values.
    self.assertEqual('1000', sampled_param.Values)

  def testCollectSampleWrap(self):
    obj_name = 'InternetGatewayDevice.LANDevice.1.WLANConfiguration.1.'
    obj_param = 'TotalBytesSent'
    sampled_param = periodic_statistics.PeriodicStatistics.SampleSet.Parameter()
    sampled_param.Enable = True
    sampled_param.Reference = obj_name + obj_param
    sample_set = periodic_statistics.PeriodicStatistics.SampleSet()
    self.mock_root.GetExport(mox.IsA(str)).AndReturn(1000)
    self.mock_root.GetExport(mox.IsA(str)).AndReturn(2000)
    self.mock_root.GetExport(mox.IsA(str)).AndReturn(3000)
    self.mock_root.GetExport(mox.IsA(str)).AndReturn(4000)
    self.mock_root.GetExport(mox.IsA(str)).AndReturn(5000)
    self.m.ReplayAll()

    sample_set.SetCpeAndRoot(cpe=self.mock_cpe, root=self.mock_root)
    sample_set.SetParameter('1', sampled_param)
    sample_set.ReportSamples = 1
    sample_set._sample_start_time = 10
    periodic_statistics.TIMEFUNC = lambda: 20
    sample_set.CollectSample()
    self.assertEqual('10', sample_set.SampleSeconds)
    self.assertEqual('10', sampled_param.SampleSeconds)
    self.assertEqual('1000', sampled_param.Values)
    # Take a second sample
    sample_set._sample_start_time = 25
    periodic_statistics.TIMEFUNC = lambda: 30
    sample_set.CollectSample()
    self.assertEqual('5', sample_set.SampleSeconds)
    self.assertEqual('5', sampled_param.SampleSeconds)
    self.assertEqual('2000', sampled_param.Values)

    # change the ReportSamples
    sample_set.ReportSamples = 3
    sample_set._sample_start_time = 24
    periodic_statistics.TIMEFUNC = lambda: 30
    sample_set.CollectSample()
    sample_set._sample_start_time = 33
    periodic_statistics.TIMEFUNC = lambda: 40
    sample_set.CollectSample()
    self.assertEqual('5,6,7', sample_set.SampleSeconds)
    self.assertEqual('5,6,7', sampled_param.SampleSeconds)
    self.assertEqual('2000,3000,4000', sampled_param.Values)
    # This next sample should cause the oldest sample to be discarded.
    sample_set._sample_start_time = 42
    periodic_statistics.TIMEFUNC = lambda: 50
    sample_set.CollectSample()
    self.assertEqual('6,7,8', sample_set.SampleSeconds)
    self.assertEqual('6,7,8', sampled_param.SampleSeconds)
    self.assertEqual('3000,4000,5000', sampled_param.Values)
    # Set ReportSamples to a smaller value and make sure old values
    # get trimmed.
    sample_set.ReportSamples = 2
    self.assertEqual('7,8', sample_set.SampleSeconds)
    self.assertEqual('7,8', sampled_param.SampleSeconds)
    self.assertEqual('4000,5000', sampled_param.Values)

  def testSampleDatetime(self):
    obj_name = 'Fakeroot.Foo.Bar.'
    obj_param = 'Baz'
    sampled_param = periodic_statistics.PeriodicStatistics.SampleSet.Parameter()
    sampled_param.Enable = True
    sampled_param.Reference = obj_name + obj_param
    sample_set = periodic_statistics.PeriodicStatistics.SampleSet()
    dt = datetime.datetime(2013, 7, 8, 12, 0, 1)
    self.mock_root.GetExport(mox.IsA(str)).AndReturn(dt)
    self.m.ReplayAll()

    sample_set.SetCpeAndRoot(cpe=self.mock_cpe, root=self.mock_root)
    sample_set.SetParameter('1', sampled_param)
    sample_set.CollectSample()
    self.assertEqual('2013-07-08T12:00:01Z', sampled_param.Values)

  def testEscapeCommas(self):
    sampled_param = periodic_statistics.PeriodicStatistics.SampleSet.Parameter()
    sampled_param.Enable = True
    sampled_param.Reference = 'Foo.CommaParameter.1.Bar'
    sample_set = periodic_statistics.PeriodicStatistics.SampleSet()
    self.mock_root.GetExport(mox.IsA(str)).AndReturn('1000,20 0')
    self.mock_root.GetExport(mox.IsA(str)).AndReturn('3%00,40$&')
    self.mock_root.GetExport(mox.IsA(str)).AndReturn('5000\t\n6000')
    self.m.ReplayAll()

    sample_set.SetCpeAndRoot(cpe=self.mock_cpe, root=self.mock_root)
    sample_set.SetParameter('1', sampled_param)
    sample_set.ReportSamples = 3
    sample_set.CollectSample()
    sample_set.CollectSample()
    sample_set.CollectSample()

    # Check that the commas within each sample were correctly escaped.
    self.assertEqual('1000%2c20%200,3%2500%2c40$&,5000%09%0a6000',
                     sampled_param.Values.lower())



class SampleSetTest(unittest.TestCase):
  def setUp(self):
    self.save_time_func = periodic_statistics.TIMEFUNC
    self.ps = periodic_statistics.PeriodicStatistics()
    self.m = mox.Mox()
    self.mock_root = self.m.CreateMock(tr.core.Exporter)
    self.mock_cpe = self.m.CreateMock(tr.http.CPEStateMachine)
    self.mock_ioloop = self.m.CreateMock(tornado.ioloop.IOLoop)
    self.mock_cpe.ioloop = self.mock_ioloop
    self.ps.SetCpe(self.mock_cpe)
    self.ps.SetRoot(self.mock_root)

  def tearDown(self):
    self.m.VerifyAll()
    periodic_statistics.TIMEFUNC = self.save_time_func

  def testValidateExports(self):
    sample_set = periodic_statistics.PeriodicStatistics.SampleSet()
    sample_set.ValidateExports()

  def testParameters(self):
    sample_set = periodic_statistics.PeriodicStatistics.SampleSet()
    param1 = periodic_statistics.PeriodicStatistics.SampleSet.Parameter()
    sample_set.ParameterList['0'] = param1
    self.assertEqual(1, sample_set.ParameterNumberOfEntries)
    for key in sample_set.ParameterList:
      self.assertEqual(key, '0')
      self.assertEqual(sample_set.ParameterList[key], param1)
    del sample_set.ParameterList['0']
    self.assertEqual(0, sample_set.ParameterNumberOfEntries)

  def testReportSamples(self):
    sample_set = periodic_statistics.PeriodicStatistics.SampleSet()
    self.assertEqual(0, sample_set.ReportSamples)
    sample_set.ReportSamples = '10'
    self.assertEqual(10, sample_set.ReportSamples)

  def testSampleInterval(self):
    sample_set = periodic_statistics.PeriodicStatistics.SampleSet()
    self.ps.SampleSetList['0'] = sample_set
    self.assertEqual(0, sample_set.SampleInterval)
    sample_set.SampleInterval = 10
    self.assertEqual(10, sample_set.SampleInterval)

  def testCollectSample(self):
    self.m.ReplayAll()
    sample_set = periodic_statistics.PeriodicStatistics.SampleSet()
    self.ps.SampleSetList['0'] = sample_set
    start1_time = time.time()
    sample_set.CollectSample()
    end1_time = time.time()
    self.assertEqual(1, len(sample_set._sample_times))
    self.assertLessEqual(start1_time, sample_set._sample_times[0][0])
    self.assertGreaterEqual(end1_time, sample_set._sample_times[0][1])
    sample_set.CollectSample()
    self.assertEqual(2, len(sample_set._sample_times))
    self.assertLess(
        sample_set._sample_times[0][0], sample_set._sample_times[1][0])
    self.assertLess(
        sample_set._sample_times[0][1], sample_set._sample_times[1][1])
    self.assertEqual(sample_set.SampleSeconds, '0,0')

  def testSampleTrigger(self):
    sample_set = periodic_statistics.PeriodicStatistics.SampleSet()
    self.ps.SampleSetList['0'] = sample_set
    self.mock_ioloop.add_timeout(mox.IsA(datetime.timedelta),
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

  def testSampleTimes(self):
    sample_set = periodic_statistics.PeriodicStatistics.SampleSet()
    sample_set._sample_times = []
    self.assertEqual('', sample_set.SampleSeconds)
    self.assertEqual('0001-01-01T00:00:00Z', sample_set.ReportStartTime)

    sample_time1 = (10.0, 12.5)
    sample_time2 = (13.0, 15.7)
    sample_time3 = (20.0, 25.3)
    sample_set._sample_times.append(sample_time1)
    self.assertEqual('3', sample_set.SampleSeconds)
    sample_set._sample_times.append(sample_time2)
    self.assertEqual('3,3', sample_set.SampleSeconds)
    sample_set._sample_times.append(sample_time3)
    self.assertEqual(sample_set.SampleSeconds, '3,3,5')
    # First sample is taken at absolute time 10.0, which is 10s after
    # the epoch.
    self.assertEqual('1970-01-01T00:00:10Z', sample_set.ReportStartTime)

  def testPassiveNotify(self):
    sample_set = periodic_statistics.PeriodicStatistics.SampleSet()
    self.m.StubOutWithMock(sample_set, 'ClearSamplingData')
    self.m.StubOutWithMock(sample_set, 'SetSampleTrigger')
    PARAMETER = periodic_statistics.PeriodicStatistics.SampleSet.Parameter
    mock_param1 = self.m.CreateMock(PARAMETER)
    mock_param2 = self.m.CreateMock(PARAMETER)
    mock_param1.Reference = 'Fake.Param.One'
    mock_param2.Reference = 'Fake.Param.Two'
    sample_set.ClearSamplingData()
    periodic_statistics.TIMEFUNC = lambda: 20
    mock_param1.CollectSample(start_time=10)
    mock_param2.CollectSample(start_time=10)
    sample_set.SetSampleTrigger()
    obj_name = 'Device.PeriodicStatistics.SampleSet.0'
    param_name = obj_name + '.Status'
    self.mock_root.GetCanonicalName(sample_set).AndReturn(obj_name)
    self.mock_cpe.SetNotificationParameters([(param_name, 'Trigger')])
    self.m.ReplayAll()

    self.assertEqual({}, sample_set._parameter_list)
    sample_set._parameter_list['1'] = mock_param1
    sample_set._parameter_list['2'] = mock_param2
    sample_set.SetCpeAndRoot(cpe=self.mock_cpe, root=self.mock_root)
    self.assertEqual(0, sample_set.FetchSamples)
    sample_set.FetchSamples = 1
    sample_set._sample_start_time = 10
    self.assertEqual(1, sample_set.FetchSamples)
    sample_set._report_samples = 1
    sample_set.Enable = 'True'
    sample_set._attributes['Notification'] = 1
    periodic_statistics.TIMEFUNC = lambda: 20
    sample_set.CollectSample()

  def testActiveNotify(self):
    sample_set = periodic_statistics.PeriodicStatistics.SampleSet()
    self.m.StubOutWithMock(sample_set, 'ClearSamplingData')
    self.m.StubOutWithMock(sample_set, 'SetSampleTrigger')
    PARAMETER = periodic_statistics.PeriodicStatistics.SampleSet.Parameter
    mock_param1 = self.m.CreateMock(PARAMETER)
    mock_param2 = self.m.CreateMock(PARAMETER)
    mock_param1.Reference = 'Fake.Param.One'
    mock_param2.Reference = 'Fake.Param.Two'
    periodic_statistics.TIMEFUNC = lambda: 20
    mock_param1.CollectSample(start_time=10)
    mock_param2.CollectSample(start_time=10)
    periodic_statistics.TIMEFUNC = lambda: 20
    sample_set.SetSampleTrigger()
    obj_name = 'Device.PeriodicStatistics.SampleSet.0'
    param_name = obj_name + '.Status'
    sample_set.ClearSamplingData()
    self.mock_root.GetCanonicalName(sample_set).AndReturn(obj_name)
    self.mock_cpe.SetNotificationParameters([(param_name, 'Trigger')])
    self.mock_cpe.NewValueChangeSession()
    self.m.ReplayAll()

    self.assertEqual({}, sample_set._parameter_list)
    sample_set._parameter_list['1'] = mock_param1
    sample_set._parameter_list['2'] = mock_param2
    sample_set.SetCpeAndRoot(cpe=self.mock_cpe, root=self.mock_root)
    self.assertEqual(0, sample_set.FetchSamples)
    sample_set.FetchSamples = 1
    self.assertEqual(1, sample_set.FetchSamples)
    sample_set._report_samples = 1
    sample_set.Enable = 'True'
    sample_set._attributes['Notification'] = 2
    sample_set._sample_start_time = 10
    periodic_statistics.TIMEFUNC = lambda: 20
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
    self.assertEqual(0, len(sample_set._sample_times))
    self.assertEqual(0, len(param1._sample_times))
    self.assertEqual(0, len(param2._sample_times))
    self.assertEqual(0, len(param1._values))
    self.assertEqual(0, len(param2._values))

  def testCalcTimeToNext(self):
    # Test with no sample period set.
    sample_set = periodic_statistics.PeriodicStatistics.SampleSet()
    sample_set._sample_interval = 60
    # year, month, hour, min, sec
    start_time = time.mktime((2000, 7, 7, 6, 0, 0, -1, -1, -1))
    self.assertEqual(60, sample_set.CalcTimeToNextSample(start_time))
    self.assertEqual(50, sample_set.CalcTimeToNextSample(start_time+10))
    self.assertEqual(10, sample_set.CalcTimeToNextSample(start_time+50))
    self.assertEqual(10, sample_set.CalcTimeToNextSample(start_time+50+60*30))
    sample_set._sample_interval = 3600
    self.assertEqual(3600, sample_set.CalcTimeToNextSample(start_time))
    self.assertEqual(3599, sample_set.CalcTimeToNextSample(start_time+1))
    self.assertEqual(3599, sample_set.CalcTimeToNextSample(start_time+3601))

    sample_set.TimeReference = '2012-06-1T1:00:00.0Z'
    sample_set._sample_interval = 15  # Every 15 seconds.
    # Check time to sample if current time is 5 seconds after the timeref.
    # And check that it works if samples collected is > 0
    current_time = time.mktime((2012, 6, 1, 1, 0, 5, -1, -1, -1))
    time_till_sample = sample_set.CalcTimeToNextSample(current_time)
    self.assertEqual(10, time_till_sample)
    sample_set._samples_collected = 10
    self.assertEqual(10, time_till_sample)
    sample_set._samples_collected = 0

    # Check time to sample if current time is 16 seconds after the timeref.
    current_time = time.mktime((2012, 6, 1, 1, 0, 16, -1, -1, -1))
    time_till_sample = sample_set.CalcTimeToNextSample(current_time)
    self.assertEqual(14, time_till_sample)

    # Check time to sample if current time is 1 hour after the timeref
    current_time = time.mktime((2012, 6, 1, 2, 0, 5, -1, -1, -1))
    time_till_sample = sample_set.CalcTimeToNextSample(current_time)
    self.assertEqual(10, time_till_sample)

    # Check time to sample if current time is 1 day after the timeref
    current_time = time.mktime((2012, 6, 2, 1, 0, 0, -1, -1, -1))
    time_till_sample = sample_set.CalcTimeToNextSample(current_time)
    self.assertEqual(15, time_till_sample)

    # Check time to sample if current time is 1 day before the timeref
    current_time = time.mktime((2012, 6, 2, 1, 0, 0, -1, -1, -1))
    time_till_sample = sample_set.CalcTimeToNextSample(current_time)
    self.assertEqual(15, time_till_sample)

    # Check using TimeReference, where the time to sample would
    # be less than 1
    sample_set.TimeReference = '1970-01-01T00:00:00Z'
    sample_set.SampleInterval = 5
    time_till_sample = sample_set.CalcTimeToNextSample(current_time)
    current_time = time.mktime((2012, 6, 2, 1, 1, 4, -1, -1, -1))
    time_till_sample = sample_set.CalcTimeToNextSample(current_time)
    self.assertEqual(1, time_till_sample)
    current_time += 0.9
    time_till_sample = sample_set.CalcTimeToNextSample(current_time)
    self.assertEqual(1, time_till_sample)
    current_time += 0.2
    time_till_sample = sample_set.CalcTimeToNextSample(current_time)
    self.assertEqual(5, round(time_till_sample))

  def testFetchSamplesTriggered(self):
    sample_set = periodic_statistics.PeriodicStatistics.SampleSet()
    sample_set._report_samples = 10
    sample_set._fetch_samples = 7
    sample_set._samples_collected = 0
    self.assertFalse(sample_set.FetchSamplesTriggered())
    sample_set._samples_collected = 7
    self.assertTrue(sample_set.FetchSamplesTriggered())
    sample_set._samples_collected = 10
    self.assertFalse(sample_set.FetchSamplesTriggered())
    sample_set._samples_collected = 14
    self.assertTrue(sample_set.FetchSamplesTriggered())
    sample_set._samples_collected = 21
    self.assertTrue(sample_set.FetchSamplesTriggered())
    # Make sure 0 doesn't do anything
    sample_set._fetch_samples = 0
    sample_set._samples_collected = 10
    self.assertFalse(sample_set.FetchSamplesTriggered())
    # and if FetchSamples > ReportSamples
    sample_set._fetch_samples = 11
    sample_set._samples_collected = 11
    self.assertFalse(sample_set.FetchSamplesTriggered())
    # check FetchSamples == ReportSamples
    sample_set._report_samples = 10
    sample_set._fetch_samples = 10
    sample_set._samples_collected = 10
    self.assertTrue(sample_set.FetchSamplesTriggered())


if __name__ == '__main__':
  unittest.main()
