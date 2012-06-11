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
#pylint: disable-msg=C6409

"""Implementation of tr-157 collection of periodic statistics."""

__author__ = 'jnewlin@google.com (John Newlin)'

import datetime
import time
import tr.cwmpbool
import tr.tr157_v1_3

# TODO(jnewlin): Denton has suggested that we might need to import a newer
# version of the schema.
BASE157PS = tr.tr157_v1_3.InternetGatewayDevice_v1_7.PeriodicStatistics

CALC_MODES = frozenset(
    ['Latest', 'Minimum', 'Maximum', 'Average'])
SAMPLE_MODES = frozenset(['Current', 'Change'])


def _MakeSampleSeconds(sample_seconds):
  """Helper to convert an array of time values to a tr157 string."""
  if not len(sample_seconds):
    return ''
  # Create a new array that is just array[n] - array[n-1]
  # and then round to nearest, convert to int, and then to a string.
  deltas = map(lambda x,y: y-x, sample_seconds[:-1], sample_seconds[1:])
  deltas = [str(int(round(x))) for x in deltas]
  deltas.insert(0, '0')
  return ','.join(deltas)


class PeriodicStatistics(BASE157PS):
  """An implementation of tr157 PeriodicStatistics sampling."""

  def __init__(self):
    BASE157PS.__init__(self)
    self._root = None
    self._cpe = None
    self.sample_sets = dict()
    self.SampleSetList = tr.core.AutoDict(
        'PeriodicStatistics.SampleSetList', iteritems=self.IterSampleSets,
        getitem=self.GetSampleSet, setitem=self.SetSampleSet,
        delitem=self.DelSampleSet)

  @property
  def SampleSet(self):
    return dm.periodic_statistics.SampleSet()

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

  def StartTransaction(self):
    # TODO(jnewlin): Implement the transaction model for SetParameterValues
    pass

  def AbandonTransaction(self):
    pass

  def CommitTransaction(self):
    pass

  def IterSampleSets(self):
    return self.sample_sets.iteritems()

  def GetSampleSet(self, key):
    return self.sample_sets[key]

  def SetSampleSet(self, key, value):
    value.SetCpeAndRoot(self._cpe, self._root)
    self.sample_sets[key] = value

  def DelSampleSet(self, key):
    del self.sample_sets[key]

  @property
  def SampleSetNumberOfEntries(self):
    return len(self.sample_sets)

  @property
  def MaxReportSamples(self):
    """Maximum samples that can be collected in a report.

    Returns:
      A value of 0 in this case, indicates no specific maximum.
    """
    return 0

  @property
  def MinSampleInterval(self):
    """Minimum sampling interval, a value of 0 indicates no minimum."""
    return 0

  class SampleSet(BASE157PS.SampleSet):
    """Implementation of PeriodicStatistics.SampleSet."""

    def __init__(self):
      BASE157PS.SampleSet.__init__(self)
      self.ParameterList = tr.core.AutoDict(
          'ParameterList', iteritems=self.IterParameters,
          getitem=self.GetParameter, setitem=self.SetParameter,
          delitem=self.DelParameter)
      self.Unexport('ForceSample')
      self.Name = ''
      self.ParameterNumberOfEntries = 0
      self.TimeReference = 0
      self._parameter_list = dict()
      self._sample_seconds = []
      self._attributes = dict()
      self._cpe = None
      self._root = None
      self._enable = False
      self._pending_timeout = None
      self._fetch_samples = 0
      self._report_samples = 0
      self._sample_interval = 0
      self._report_start_time = 0
      self._report_end_time = 0

    def IterParameters(self):
      return self._parameter_list.iteritems()

    def GetParameter(self, key):
      return self._parameter_list[key]

    def SetParameter(self, key, value):
      self._parameter_list[key] = value
      value.SetParent(self)
      value.SetRoot(self._root)

    def DelParameter(self, key):
      del self._parameter_list[key]

    @property
    def ReportStartTime(self):
      return tr.cwmpdate.format(self._report_start_time)

    @property
    def ReportEndTime(self):
      return tr.cwmpdate.format(self._report_end_time)

    @property
    def Status(self):
      return 'Disabled' if self.FinishedSampling() else 'Enabled'

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
      self.RemoveTimeout()
      time_to_sample = self.CalcTimeToNextSample()
      delta = datetime.timedelta(0, time_to_sample)
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
      self._sample_seconds = []
      self._report_start_time = 0
      self._report_end_time = 0
      for param in self._parameter_list.itervalues():
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

    def FinishedSampling(self):
      """Returns True if we are done sample for this set."""
      if not self._enable or len(self._sample_seconds) >= self.ReportSamples:
        return True
      return False

    def CalcTimeToNextSample(self):
      """Return time until the next sample should be collected."""
      # TODO(jnewlin): Make this work with the TR157- TimeReference.
      # currently we'll just start a sample every SampleInterval.
      return self._sample_interval

    def CollectSample(self):
      """Collects a sample for each of the Parameters.

      Iterate over all of the Parameter objects and collect samples
      for each of those.  If this is the last sample, optionally signal
      back to the ACS that the sampling is finished.  If another sample
      is required, setup a trigger to collect the next sample.
      TODO(jnewlin): Add code to trigger the ACS.
      """
      self.RemoveTimeout()
      if not self._root or not self._cpe:
        return

      current_time = time.time()
      if len(self._sample_seconds) == 0:
        self._report_start_time = current_time
      self._report_end_time = current_time
      self._sample_seconds.append(current_time)

      for key in self._parameter_list:
        self._parameter_list[key].CollectSample()

      if not self.FinishedSampling():
        self.SetSampleTrigger()

      if len(self._sample_seconds) == self.FetchSamples:
        if self.PassiveNotification() or self.ActiveNotification():
          param_name = self._root.GetCanonicalName(self)
          param_name += '.Status'
          self._cpe.SetNotificationParameters(
              [(param_name, self.Status)])
          if self.ActiveNotification():
            self._cpe.NewValueChangeSession()

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
      return _MakeSampleSeconds(self._sample_seconds)

    def SetAttribute(self, attr, value):
      """Sets an attribute on this object.  Currently can be anything.

      NOTE(jnewlin):
      This should probably throw an exception for unsupported attributes
      and the list of attributes should come for the tr xml spec files
      somewhere, but it's not clear to me how to do this.

      Args:
        attr: the name of the attribute to set.
        value: the value of the attribute
      """
      if attr == 'Notification':
        # Technically should not overwrite this unless we all see a
        # 'NotificationChange' with a value of true.  Seems a bit retarded
        # though, why send a SetParametersAttribute with a new value but
        # NotificationChange set to False...
        self._attributes[attr] = int(value)
      elif attr == 'AccessList':
        self._attributes[attr] = value

    class Parameter(BASE157PS.SampleSet.Parameter):
      """Implementation of PeriodicStatistics.SampleSet.Parameter."""

      def __init__(self):
        BASE157PS.SampleSet.Parameter.__init__(self)
        self._parent = None
        self._root = None
        self.Enable = False
        self.HighThreshold = 0
        self.LowThreshold = 0
        self.Reference = None
        self._calculation_mode = 'Latest'
        self._failures = 0
        self._sample_mode = 'Current'
        self._sample_seconds = []
        self._suspect_data = []
        self._values = []

      @property
      def CalculationMode(self):
        return self._calculation_mode

      @CalculationMode.setter
      def CalculationMode(self, value):
        if not value in CALC_MODES:
          raise ValueError('Bad value sent for CalculationMode.')
        self._calculation_mode = value

      @property
      def Failures(self):
        return self._failures

      @property
      def SampleMode(self):
        return self._sample_mode

      @SampleMode.setter
      def SampleMode(self, value):
        if value not in SAMPLE_MODES:
          raise ValueError('Bad value set for SampleMode: ' + str(value))
        self._sample_mode = value

      @property
      def SampleSeconds(self):
        """Convert the stored time values to a SampleSeconds string."""
        return _MakeSampleSeconds(self._sample_seconds)

      @property
      def SuspectData(self):
        return ','.join(self._suspect_data)

      @property
      def Values(self):
        return ','.join(self._values)

      def SetParent(self, parent):
        """Set the parent object (should be a SampleSet)."""
        self._parent = parent

      def SetRoot(self, root):
        """Sets the root of the hierarchy, needed for GetExport."""
        self._root = root

      def CollectSample(self):
        """Collects one new sample point."""
        if not self.Enable:
          return
        try:
          # TODO(jnewlin): Update _suspect_data.
          current_value = self._root.GetExport(self.Reference)
          self._values.append(str(current_value))
          self._sample_seconds.append(time.time())
        except (KeyError, AttributeError):
          pass

      def ClearSamplingData(self):
        """Throw away any sampled data."""
        self._values = []
        self._sample_seconds = []

def main():
  pass

if __name__ == '__main__':
  main()
