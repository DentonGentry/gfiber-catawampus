#!/usr/bin/python
# Copyright 2015 Google Inc. All Rights Reserved.
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
#
"""The specific root data models our system is based on.

To avoid mismatching data models (inheriting some of our implementations
from old models and some from new models) we alias them here.  That way,
we can upgrade to a new data model just by changing one place (and then
presumably getting lots of errors from tr.core.Exporter.ValidateSchema()
until all the new features are implemented or explicitly Unexported.)
"""
import google3
import tr.x_catawampus_storage_1_0 as storage
import tr.x_catawampus_tr098_1_0 as tr098
import tr.x_catawampus_tr181_2_0 as tr181


Device = tr181.X_CATAWAMPUS_ORG_Device_v2_0.Device
InternetGatewayDevice = (
    tr098.X_CATAWAMPUS_ORG_InternetGatewayDevice_v1_0.InternetGatewayDevice)
Storage = storage.X_CATAWAMPUS_ORG_Storage_v1_0
