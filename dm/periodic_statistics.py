#!/usr/bin/python
#
# Copyright 2012 Google Inc. All Rights Reserved.
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
#
# TR-069 has mandatory attribute names that don't comply with policy
# pylint:disable=invalid-name

"""Implementation of tr-157 collection of periodic statistics."""

__author__ = 'jnewlin@google.com (John Newlin)'

import datetime
import time
import tr.api_soap
import tr.cwmpbool
import tr.cwmptypes
import tr.handle
import tr.monohelper
import tr.session
import tr.tr157_v1_3


def _timefunc():
  return time.time()


# TODO(jnewlin): Denton has suggested that we might need to import a newer
# version of the schema.
BASE157PS = tr.tr157_v1_3.Device_v1_7.Device.PeriodicStatistics

# The spec says when TimeReference isn't set, we can pick the phase.  This
# seems as good as any other.  Set the phase to start at the beginning of
# a day/hour/minute/second.
DEFAULT_TIME_REF_SEC = time.mktime((1970, 1, 1, 0, 0, 0, -1, -1, -1))
TIMEFUNC = _timefunc


# Profiling which parameters take the most time to sample.
# pylint:disable=g-bad-name
ExpensiveStatsEnable = False
ExpensiveStats = {}


def _MakeSampleSeconds(sample_times):
  """Helper to convert an array of time values to a tr157 string."""
  deltas = [str(int(round(end - start))) for start, end in sample_times]
  return ','.join(deltas)


_needs_flush = True


def _EnableFlush():
  global _needs_flush
  _needs_flush = True


def _FlushIfNewStatsSession(loop):
  """Flush the tr.session cache, but max once per ioloop iteration.

  This takes advantage of the fact that all add_callback() calls are run
  together, separately from timeouts.  So each SampleSet has its own timeout,
  and (if multiple ones trigger in a single iteration) this function gets
  called more than once, but only flushes once.  After all those timeouts
  run, _EnableFlush() might get called one or many times, which just sets
  a bool (so there's no point deduplicating the calls) that allows another
  cache flush when more timeouts occur.

  Args:
    loop: the tornado ioloop object to use for flush control.
  """
  global _needs_flush
  if _needs_flush:
    loop.add_callback(_EnableFlush)
    tr.session.cache.flush()
    _needs_flush = False


class _SampleSetDict(dict):

  def __delitem__(self, k):
    v = self[k]
    v.Shutdown()
    dict.__delitem__(self, k)


class PeriodicStatistics(BASE157PS):
  """An implementation of tr157 PeriodicStatistics sampling."""

  MaxReportSamples = tr.cwmptypes.ReadOnlyUnsigned(0)
  MinSampleInterval = tr.cwmptypes.ReadOnlyUnsigned(0)
  SampleSetNumberOfEntries = tr.cwmptypes.NumberOf('SampleSetList')

  def __init__(self):
    super(PeriodicStatistics, self).__init__()
    self._root = None
    self._cpe = None
    self.SampleSetList = _SampleSetDict()

  def SetRoot(self, root):
    """Sets the root object.

    Args:
      root: The root of the tr hierarchy.

    This is needed to lookup objects that are being tracked.
    """
    self._root = root

  def SetCpe(self, cpe):
    """Sets the cpe to use for scheduling polling events."""
    self._cpe = cpe

  def SampleSet(self):
    v = SampleSet()
    v.SetCpeAndRoot(self._cpe, self._root)
    return v


@tr.core.Unexports(['ForceSample'])
class SampleSet(BASE157PS.SampleSet):
  """Implementation of PeriodicStatistics.SampleSet."""

  ParameterNumberOfEntries = tr.cwmptypes.NumberOf('ParameterList')

  def __init__(self):
    super(BASE157PS.SampleSet, self).__init__()
    self.ParameterList = {}
    self.Name = ''
    self._sample_times = ()
    self._samples_collected = 0
    self._sample_start_time = None
    self._attributes = dict()
    self._cpe = None
    self._root = None
    self._canonicalname = None
    self._enable = False
    self._pending_timeout = None
    self._fetch_samples = 0
    self._report_samples = 0
    self._sample_interval = 0
    self._time_reference = None

  def Parameter(self):
    return Parameter()

  def Shutdown(self):
    """Called when this object is no longer sampling."""
    self.ParameterList.clear()
    self.RemoveTimeout()

  @property
  def TimeReference(self):
    # if _time_reference is None, this returns a CWMP
    # Unknown time.
    return tr.cwmpdate.format(self._time_reference)

  @TimeReference.setter
  def TimeReference(self, value):
    self.ClearSamplingData()
    if value == '0001-01-01T00:00:00Z':  # CWMP Unknown time.
      self._time_reference = None
    else:
      self._time_reference = tr.cwmpdate.parse(value)

  @property
  def ReportStartTime(self):
    start_time = self._sample_times[0][0] if self._sample_times else None
    return tr.cwmpdate.format(start_time)

  @property
  def ReportEndTime(self):
    end_time = self._sample_times[-1][1] if self._sample_times else None
    return tr.cwmpdate.format(end_time)

  @property
  def Status(self):
    return 'Enabled' if self._enable else 'Disabled'

  @property
  def FetchSamples(self):
    return self._fetch_samples

  @FetchSamples.setter
  def FetchSamples(self, value):
    self._fetch_samples = int(value)

  @property
  def ReportSamples(self):
    return self._report_samples

  @ReportSamples.setter
  def ReportSamples(self, value):
    v = int(value)
    if v < 1:
      raise ValueError('ReportSamples must be >= 1')
    self._report_samples = v
    # Trim down samples
    self._sample_times = self._sample_times[-v:]
    for param in self.ParameterList.itervalues():
      param.TrimSamples(v)
    self.UpdateSampling()

  @property
  def SampleInterval(self):
    return self._sample_interval

  @SampleInterval.setter
  def SampleInterval(self, value):
    v = int(value)
    if v < 1:
      raise ValueError('SampleInterval must be >= 1')
    self._sample_interval = v
    self.ClearSamplingData()
    self.UpdateSampling()

  def RemoveTimeout(self):
    """If there is a pending timeout, removes it."""
    if self._pending_timeout:
      self._cpe.ioloop.remove_timeout(self._pending_timeout)
      self._pending_timeout = None

  def SetSampleTrigger(self):
    """Sets the timeout to collect the next sample."""
    current_time = TIMEFUNC()
    self.RemoveTimeout()
    self._sample_start_time = current_time
    time_to_sample = self.CalcTimeToNextSample(current_time)
    delta = datetime.timedelta(0, microseconds=(time_to_sample + 0.1) * 1e6)
    self._pending_timeout = self._cpe.ioloop.add_timeout(
        delta, self.CollectSample)

  def StopSampling(self):
    """Disables the sampling, and if a sample is pending, cancels it."""
    self.RemoveTimeout()

  def ClearSamplingData(self):
    """Clears out any old sampling data.

    Clears any old sampled data, so that a new sampling run can
    begin.  Also clears all Parameter objects.
    """
    self._sample_times = ()
    self._samples_collected = 0
    for param in self.ParameterList.itervalues():
      param.ClearSamplingData()

  def UpdateSampling(self):
    """This is called whenever some member is changed.

    Whenever a member, e.g. Enable is changed, call this to start
    the sampling process.
    """
    if (self._enable and self._report_samples > 0 and
        self._sample_interval > 0):
      self.SetSampleTrigger()
    else:
      self.StopSampling()

  def CalcTimeToNextSample(self, current_time):
    # Don't allow intervals less than 1, that could be bad.
    interval = max(1, self._sample_interval)
    # self._time_reference is a datetime object.
    ref_seconds = DEFAULT_TIME_REF_SEC
    if self._time_reference is not None:
      ref_seconds = time.mktime(self._time_reference.timetuple())
    delta_seconds = (current_time - ref_seconds) % interval
    tts = interval - delta_seconds
    return max(1, tts)

  def _CanonicalName(self):
    if not self._root:
      return None
    if not self._canonicalname:
      self._canonicalname = tr.handle.Handle.GetCanonicalName(
          self._root.obj, self)
    return self._canonicalname

  def CollectSample(self):
    """Collects a sample for each of the Parameters.

    Iterate over all of the Parameter objects and collect samples
    for each of those.  If this is the last sample, optionally signal
    back to the ACS that the sampling is finished.  If another sample
    is required, setup a trigger to collect the next sample.
    """
    self.RemoveTimeout()
    if not self._root or not self._cpe:
      return

    # We're starting what is effectively a CWMP session, one without such
    # trifling details as an ACS. We don't want stale data from previous
    # stats collections and/or actual ACS sessions.
    _FlushIfNewStatsSession(self._cpe.ioloop)

    use_time = TIMEFUNC()
    sample_start_time = self._sample_start_time
    if not sample_start_time:
      sample_start_time = use_time
    self._sample_start_time = None
    sample_end_time = use_time
    self._samples_collected += 1
    self._sample_times += ((sample_start_time, sample_end_time),)
    # This will keep just the last ReportSamples worth of samples.
    self._sample_times = self._sample_times[-self._report_samples:]

    for p in self.ParameterList.itervalues():
      p.CollectSample(parent=self, start_time=sample_start_time)

    if self.FetchSamplesTriggered():
      if self.PassiveNotification() or self.ActiveNotification():
        print 'FetchSample: %r' % (self.Name,)
        param_name = self._CanonicalName()
        param_name += '.Status'
        self._cpe.SetNotificationParameters(
            [(param_name, 'Trigger')])
        if self.ActiveNotification():
          self._cpe.NewValueChangeSession()

    # Do this last to get the trigger better aligned with when it's
    # supposed to fire.
    if self._enable:
      self.SetSampleTrigger()

  def FetchSamplesTriggered(self):
    """Check if FetchSamples would have triggered on this sample."""
    # If there are no samples, it's not triggered.
    if self._samples_collected == 0:
      return False

    # Per spec: To disable this trigger mechanism and still collect sampled
    # statistics, FetchSamples can be set to either 0 or a value greater
    # than ReportSamples.
    if self._fetch_samples <= 0 or self._fetch_samples > self._report_samples:
      return False

    # Check for a multiple of fetch_samples for the trigger.
    return (self._samples_collected % self._fetch_samples) == 0

  def PassiveNotification(self):
    """Check if passive notification is enabled."""
    if 'Notification' in self._attributes:
      val = self._attributes['Notification'] == 1
      return val
    return False

  def ActiveNotification(self):
    """Check if active notification is enabled."""
    if 'Notification' in self._attributes:
      val = self._attributes['Notification'] == 2
      return val
    return False

  def SetCpeAndRoot(self, cpe, root):
    self._cpe = cpe
    self._root = root

  @property
  def Enable(self):
    return self._enable

  @Enable.setter
  def Enable(self, value):
    self._enable = tr.cwmpbool.parse(value)
    if self._enable:
      self.ClearSamplingData()
    self.UpdateSampling()

  @property
  def SampleSeconds(self):
    """A comma separarted string of unsigned integers."""
    return _MakeSampleSeconds(self._sample_times)

  def SetAttributes(self, attrs):
    """Sets attributes on this object.

    These attributes are supported:
      Notification: boolean.  Only takes affect if NotificationChange is
                    also sent and True.
      AccessList: Array of zero or more entities for which write access
                  is granted.  Only the special value "Subscriber" can
                  be included.  Only takes affect if AccessListChange is
                  also present and True.

      NOTE(jnewlin):
      This should probably throw an exception for unsupported attributes.
      The list of attributes should come for the tr xml spec files,
      but it's not clear to me how to do this.

    Args:
      attrs: key/value pair of attributes to set.
    """
    if ('Notification' in attrs and
        'NotificationChange' in attrs and
        tr.cwmpbool.parse(attrs['NotificationChange'])):
      self._attributes['Notification'] = int(attrs['Notification'])

    if ('AccessList' in attrs and
        'AccessListChange' in attrs and
        tr.cwmpbool.parse(attrs['AccessListChange'])):
      self._attributes['AccessList'] = str(attrs['AccessList'])


class Parameter(BASE157PS.SampleSet.Parameter):
  """Implementation of PeriodicStatistics.SampleSet.Parameter."""

  __slots__ = ('_parent', 'Reference', '_sample_times',
               '_suspect_data', '_values', '_logged', '__weakref__')

  CalculationMode = tr.cwmptypes.Enum(
      ['Latest', 'Minimum', 'Maximum', 'Average'],
      'Latest')
  Enable = tr.cwmptypes.Bool(False)
  HighThreshold = tr.cwmptypes.Unsigned(0)
  LowThreshold = tr.cwmptypes.Unsigned(0)
  SampleMode = tr.cwmptypes.Enum(['Current', 'Change'], 'Current')

  def __init__(self):
    BASE157PS.SampleSet.Parameter.__init__(self)
    self.Reference = None
    self._sample_times = ()
    self._values = ()
    self._logged = False

  @property
  def Failures(self):
    return 0

  @property
  def SampleSeconds(self):
    """Convert the stored time values to a SampleSeconds string."""
    return _MakeSampleSeconds(self._sample_times)

  def _tr106_escape(self, value):
    """Escape string according to tr-106 section 3.2.3.

       '...Any whitespace or comma characters within an item value
        MUST be escaped using percent encoding as specified in
        Section 2.1/RFC 3986.'

    Args:
      value: a list of sampled parameters

    Returns:
      a list with whitespace and commas escaped for each sample.
    """
    escaped = value
    escaped = [x.replace('%', '%25') for x in escaped]
    escaped = [x.replace(',', '%2c') for x in escaped]
    escaped = [x.replace(' ', '%20') for x in escaped]
    escaped = [x.replace('\t', '%09') for x in escaped]
    escaped = [x.replace('\n', '%0a') for x in escaped]
    escaped = [x.replace('\r', '%0d') for x in escaped]
    return escaped

  @property
  def SuspectData(self):
    suspect_data = ()  # TODO(apenwarr): we never set this anyway
    return ','.join(self._tr106_escape(suspect_data))

  @property
  def Values(self):
    return ','.join(self._tr106_escape(self._values))

  def CollectSample(self, parent, start_time):
    """Collects one new sample point."""
    current_time = TIMEFUNC()
    start = tr.monohelper.monotime()
    if not self.Enable:
      return
    f = parent._root.GetExport  # pylint:disable=protected-access
    try:
      try:
        # TODO(jnewlin): Update _suspect_data.
        current_value = f(self.Reference)
      except (KeyError, AttributeError, IndexError), e:
        if not self._logged:
          print 'CollectSample("%s") error: %r' % (self.Reference, e)
          self._logged = True
      else:
        (_, soapstring) = tr.api_soap.Soapify(current_value)
        self._values += (soapstring,)
        self._sample_times += ((start_time, current_time),)
    finally:
      # This will keep just the last ReportSamples worth of samples.
      self.TrimSamples(parent.ReportSamples)
    end = tr.monohelper.monotime()
    if ExpensiveStatsEnable:
      accumulated = ExpensiveStats.get(self.Reference, 0.0)
      accumulated += end - start
      ExpensiveStats[self.Reference] = accumulated

  def ClearSamplingData(self):
    """Throw away any sampled data."""
    self._values = ()
    self._sample_times = ()

  def TrimSamples(self, length):
    """Trim any sampling data arrays to only keep the last N values."""
    # Make sure some bogus value of length can't be passed in.
    if length <= 0:
      length = 1
    self._sample_times = self._sample_times[-length:]
    self._values = self._values[-length:]
