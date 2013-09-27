#!/usr/bin/python
# Copyright 2011 Google Inc. All Rights Reserved.
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
#pylint: disable-msg=C6409
#pylint: disable-msg=W0404
#
"""Implement the X_GOOGLE-COM_GVSB vendor data model."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import copy
import google3
import tr.types
import tr.x_gvsb_1_0

# Unit tests can override these.
EPGPRIMARYFILE = ['/tmp/epgprimary']
EPGSECONDARYFILE = ['/tmp/epgsecondary']
EPGURLFILE = ['/tmp/epgurl']
GVSBCHANNELFILE = ['/tmp/gvsbchannel']
GVSBKICKFILE = ['/tmp/gvsbkick']
GVSBSERVERFILE = ['/tmp/gvsbhost']


class Gvsb(tr.x_gvsb_1_0.X_GOOGLE_COM_GVSB_v1_1):
  """Implementation of x-gvsb.xml."""
  EpgPrimary = tr.types.FileBacked(
      EPGPRIMARYFILE, tr.types.String(), delete_if_empty=False)
  EpgSecondary = tr.types.FileBacked(
      EPGSECONDARYFILE, tr.types.String(), delete_if_empty=False)
  EpgUrl = tr.types.FileBacked(
      EPGURLFILE, tr.types.String(), delete_if_empty=False)
  GvsbChannelLineup = tr.types.FileBacked(
      GVSBCHANNELFILE, tr.types.String(), delete_if_empty=False)
  GvsbKick = tr.types.FileBacked(
      GVSBKICKFILE, tr.types.String(), delete_if_empty=False,
      file_owner='video', file_group='video')
  GvsbServer = tr.types.FileBacked(
      GVSBSERVERFILE, tr.types.String(), delete_if_empty=False)

  def __init__(self):
    super(Gvsb, self).__init__()
    self.EpgPrimary = ''
    self.EpgSecondary = ''
    self.EpgUrl = ''
    self.GvsbChannelLineup = '0'
    self.GvsbKick = ''
    self.GvsbServer = ''
