#!/usr/bin/python
# Copyright 2016 Google Inc. All Rights Reserved.
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

# TR-069 has mandatory attribute names that don't comply with policy
# pylint:disable=invalid-name
#
"""Device.IP.Diagnostics.
"""

import google3
import dm.traceroute
import tr.basemodel
import tr.cwmptypes
import tr.experiment
import tr.x_catawampus_tr181_2_0


BASE_IPDIAG = tr.basemodel.Device.IP.Diagnostics
EXTRAPINGFILE4 = ['/tmp/extra_ping_servers']
EXTRAPINGFILE6 = ['/tmp/extra_ping6_servers']

# This is the Alexa US top 25 of 6/2016, omitting the sites which do not
# respond to ICMP ping: amazon.com, ebay.com, netflix.com, live.com,
# chase.com, paypal.com, msn.com, bankofamerica.com, cnn.com
ALEXA_V4_US = ('google.com,facebook.com,youtube.com,yahoo.com,wikipedia.org,'
               'twitter.com,reddit.com,linkedin.com,craigslist.com,'
               'pinterest.com,bing.com,imgur.com,go.com,instagram.com,'
               'diply.com,tumblr.com')
# Also omit sites which do not respond to IPv6 ping.
ALEXA_V6_US = ('google.com,facebook.com,youtube.com,yahoo.com,wikipedia.org,'
               'linkedin.com,diply.com')


@tr.experiment.Experiment
def ExtraPingAlexaUS(_):
  return [
      ('Device.IP.Diagnostics.X_CATAWAMPUS-ORG_ExtraPing4Servers', ALEXA_V4_US),
      ('Device.IP.Diagnostics.X_CATAWAMPUS-ORG_ExtraPing6Servers', ALEXA_V6_US)]


class IPDiagnostics(BASE_IPDIAG):
  """tr-181 Device.IP.Diagnostics for Google Fiber platforms."""

  X_CATAWAMPUS_ORG_ExtraPing4Servers = tr.cwmptypes.FileBacked(
      EXTRAPINGFILE4, tr.cwmptypes.String(), delete_if_empty=True)
  X_CATAWAMPUS_ORG_ExtraPing6Servers = tr.cwmptypes.FileBacked(
      EXTRAPINGFILE6, tr.cwmptypes.String(), delete_if_empty=True)

  def __init__(self, httpdownload=None, isostream=None, speedtest=None):
    super(IPDiagnostics, self).__init__()
    self.Unexport(objects=['IPPing', 'UploadDiagnostics',
                           'UDPEchoConfig', 'DownloadDiagnostics'])
    self.TraceRoute = dm.traceroute.TraceRoute()
    if httpdownload:
      self.X_CATAWAMPUS_ORG_HttpDownload = httpdownload
      self.Export(objects=['X_CATAWAMPUS-ORG_HttpDownload'])
    if isostream:
      self.X_CATAWAMPUS_ORG_Isostream = isostream
      self.Export(objects=['X_CATAWAMPUS-ORG_Isostream'])
    if speedtest:
      self.X_CATAWAMPUS_ORG_Speedtest = speedtest
      self.Export(objects=['X_CATAWAMPUS-ORG_Speedtest'])
