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
# pylint:disable=invalid-name
#
"""Implement the X_GOOGLE-COM_SSH vendor data model."""

__author__ = 'sledbetter@google.com (Shawn Ledbetter)'

import copy
import google3
import os
import random
import subprocess
import tr.x_ssh_1_0

# Unit tests can override these.
AUTHORIZED_KEYS = '/user/sshd/authorized_keys'
CAFILE = '/user/sshd/ca.pem'
CERTFILE = '/user/sshd/clientcert.pem'
KEYFILE = '/user/sshd/clientkey.pem'
FAILSAFE_KEYS = '/etc/failsafe_keys'
PROC_IF_INET6 = '/proc/net/if_inet6'


class SSHConfig(object):
  """A dumb data object to store config settings."""
  pass


class Ssh(tr.x_ssh_1_0.X_GOOGLE_COM_SSH_v1_1):
  """Implementation of x-ssh.xml."""

  def __init__(self):
    super(Ssh, self).__init__()
    self.config = self.DefaultConfig()
    self.failsafe_keys = self.ReadFile(FAILSAFE_KEYS)
    if not os.path.exists(os.path.dirname(AUTHORIZED_KEYS)):
      os.makedirs(os.path.dirname(AUTHORIZED_KEYS), 0755)
    self.WriteFile(AUTHORIZED_KEYS, self.failsafe_keys)

  def DefaultConfig(self):
    obj = SSHConfig()
    obj.enabled = False
    obj.authorized_keys = ''
    obj._tunnel_host = ''
    obj._tunnel_port = 0
    obj._ca_data = ''
    obj._key_data = ''
    obj._cert_data = ''
    obj._proxy = None
    return obj

  def StartTransaction(self):
    config = self.config
    self.config = copy.copy(config)
    self.old_config = config

  def AbandonTransaction(self):
    self.config = self.old_config
    self.old_config = None

  def CommitTransaction(self):
    self._ConfigureSsh()
    self.old_config = None

  def GetAuthorizedKeys(self):
    return self.config.authorized_keys

  def SetAuthorizedKeys(self, value):
    self.config.authorized_keys = value

  AuthorizedKeys = property(GetAuthorizedKeys, SetAuthorizedKeys, None,
                            'X_SSH.AuthorizedKeys')

  def GetEnabled(self):
    return self.config.enabled

  def SetEnabled(self, value):
    self.config.enabled = value

  Enabled = property(GetEnabled, SetEnabled, None,
                     'X_SSH.Enabled')

  def GetTunnelHost(self):
    return self.config._tunnel_host

  def SetTunnelHost(self, value):
    self.config._tunnel_host = value

  TunnelHost = property(GetTunnelHost, SetTunnelHost, None,
                        'X_SSH.TunnelHost')

  def GetTunnelPort(self):
    return self.config._tunnel_port

  def SetTunnelPort(self, value):
    self.config._tunnel_port = value

  TunnelPort = property(GetTunnelPort, SetTunnelPort, None,
                        'X_SSH.TunnelPort')

  def GetTunnelCAData(self):
    return self.config._ca_data

  def SetTunnelCAData(self, value):
    self.config._ca_data = value

  TunnelCAData = property(GetTunnelCAData, SetTunnelCAData, None,
                          'X_SSH.TunnelCAData')

  def GetTunnelKeyData(self):
    return self.config._key_data

  def SetTunnelKeyData(self, value):
    self.config._key_data = value

  TunnelKeyData = property(GetTunnelKeyData, SetTunnelKeyData, None,
                           'X_SSH.TunnelKeyData')

  def GetTunnelCertData(self):
    return self.config._cert_data

  def SetTunnelCertData(self, value):
    self.config._cert_data = value

  TunnelCertData = property(GetTunnelCertData, SetTunnelCertData, None,
                            'X_SSH.TunnelCertData')

  def WriteFile(self, filename, content):
    try:
      with open(filename, 'w') as f:
        f.write(content)
      return True
    except IOError:
      return False

  def ReadFile(self, filename):
    try:
      with open(filename, 'r') as f:
        return f.read()
    except IOError:
      return ''

  def _ConfigureSsh(self):
    if self.config.authorized_keys != self.old_config.authorized_keys:
      if self.WriteFile(AUTHORIZED_KEYS,
                        str(self.config.authorized_keys) +
                        str(self.failsafe_keys)):
        self.old_config.authorized_keys = self.config.authorized_keys

    if self.config._ca_data != self.old_config._ca_data:
      if self.WriteFile(CAFILE,
                        str(self.config._ca_data)):
        self.old_config._ca_data = self.config._ca_data

    if self.config._key_data != self.old_config._key_data:
      if self.WriteFile(KEYFILE,
                        str(self.config._key_data)):
        self.old_config._key_data = self.config._key_data

    if self.config._cert_data != self.old_config._cert_data:
      if self.WriteFile(CERTFILE,
                        str(self.config._cert_data)):
        self.old_config._cert_data = self.config._cert_data

    if self.config.enabled != self.old_config.enabled:
      if not self.config.enabled:
        self.config._proxy.terminate()
      if self.config.enabled and not self.config._proxy:
        try:
          # babysit 15 /usr/bin/reverseproxy.py | logos revproxy &
          self.config._proxy = subprocess.Popen([
              'babysit', '15',
              '/usr/bin/reverseproxy.py',
              self.config._tunnel_host,
              self.config._tunnel_port
          ], stdout=subprocess.PIPE)
          self.config._logger = subprocess.Popen([
              'logos', 'revproxy'
          ], stdin=self.config._proxy.stdout)
          self.config.enabled = True
        except subprocess.CalledProcessError:
          self.config.enabled = False
