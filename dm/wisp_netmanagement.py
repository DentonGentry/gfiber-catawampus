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

"""Implementation of TR-69 objects for WISP NetManagement.

Documentation on the JSON fields that NetManagement receives can be found at:
http://go/chimera-netmanagement-json-mappings
"""

__author__ = 'drivkin@google.com (Dennis Rivkin)'

import json
import google3
import os
import tr.cwmptypes
import tr.helpers
import tr.mainloop
import tr.x_catawampus_tr181_2_0

BASE = tr.x_catawampus_tr181_2_0.X_CATAWAMPUS_ORG_Device_v2_0
CATA181NETMANAGEMENT = BASE.Device.X_CATAWAMPUS_ORG.WispNetManagement

# These can be overridden by unit tests.
CFG_JSON_FILE = '/fiber/config/chimera-cfg.json'


class WispNetManagement(CATA181NETMANAGEMENT):
  """Device.X_CATAWAMPUS_ORG.WispNetManagement."""

  def __init__(self):
    super(WispNetManagement, self).__init__()
    self._configuration = self._LoadJsonFromFile(CFG_JSON_FILE)

  def _SetConfiguration(self, value):
    if not value:
      raise ValueError('configuration must not be empty')

    # value must be in a JSON format, raise exception if not.
    self._configuration = json.dumps(json.loads(value))

    self._WriteConfig()

  def _GetConfiguration(self):
    return self._configuration

  Configuration = property(_GetConfiguration, _SetConfiguration, None,
                           'WispNetManagement.Configuration')

  def _WriteConfig(self):
    """Write out WispNetManagement new configuration."""

    print 'Writing WispNetManagement new configuration %s' % self._configuration
    with tr.helpers.AtomicFile(CFG_JSON_FILE) as f:
      f.write(self._configuration)

  def _LoadJsonFromFile(self, path, json_keys=None):
    """Deserializes a JSON file to a Python object.

    Args:
      path: The path to the JSON file to be converted.
      json_keys: A string of dot-delimited keys used to point to the JSON data
                 in the dict.
    Example:
    {
      'a': {
        'b': {
          'c': {
            'param1': 1,
            'param2': 2
          }
        }
      }
    }

    json_keys = 'a.b.c'
    Expected return is:
    {
      'param1': 1,
      'param2': 2
    }

    Returns:
      the JSON string
    """

    if not os.path.exists(path):
      # It is a valid state that there might not be a JSON data file yet,
      # so just return without printing an error.
      return '{}'

    with open(path) as f:
      _json_data = json.load(f)
    if json_keys:
      for key in json_keys.split('.'):
        if not _json_data.has_key(key):
          print 'JSON file %s does not have key: %s' % (path, key)
          return '{}'
        _json_data = _json_data[key]
    return json.dumps(_json_data)


if __name__ == '__main__':
  print tr.handle.DumpSchema(WispNetManagement())
