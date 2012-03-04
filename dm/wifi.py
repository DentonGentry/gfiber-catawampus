#!/usr/bin/python
#
# Copyright 2012 Google Inc. All Rights Reserved.
#
# TR-069 has mandatory attribute names that don't comply with policy
#pylint: disable-msg=C6409

"""Implementations of platform-independant tr-98/181 WLAN objects."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import tr.tr098_v1_4


def ContiguousRanges(seq):
  """Given an integer sequence, return contiguous ranges.

  This is expected to be useful for the tr-98 WLANConfig PossibleChannels
  parameter.

  Args:
    seq: a sequence of integers, like [1,2,3,4,5]

  Returns:
    A string of the collapsed ranges.
    Given [1,2,3,4,5] as input, will return '1-5'
  """
  in_range = False
  prev = seq[0]
  output = list(str(seq[0]))
  for item in seq[1:]:
    if item == prev + 1:
      if not in_range:
        in_range = True
        output.append('-')
    else:
      if in_range:
        output.append(str(prev))
      output.append(',' + str(item))
      in_range = False
    prev = item
  if in_range:
    output.append(str(prev))
  return ''.join(output)


class PreSharedKey98(tr.tr098_v1_4.InternetGatewayDevice_v1_9.InternetGatewayDevice.LANDevice.WLANConfiguration.PreSharedKey):
  def __init__(self):
    super(PreSharedKey98, self).__init__()
    self.key = None
    self.passphrase = None
    self.assoc_mac_addr = None
    self.key_pbkdf2 = None
    self.salt = None

  def GetKey(self, salt):
    """Return the key to program into the Wifi chipset.

    Args:
      salt: Per WPA2 spec, the SSID is used as the salt.
    Returns:
      The key as a hex string, or None if no key.
    """
    if self.key is not None:
      return self.key
    if self.key_pbkdf2 is None or salt != self.salt:
      self.salt = salt
      self.key_pbkdf2 = self._GeneratePBKDF2(salt)
    if self.key_pbkdf2 is not None:
      return self.key_pbkdf2
    return None

  def _GeneratePBKDF2(self, salt):
    """Compute WPA2 key from a passphrase."""
    if self.passphrase is None:
      return None
    return pbkdf2.pbkdf2_hex(self.passphrase, salt, iterations=4096, keylen=32)

  def SetPreSharedKey(self, value):
    self.key = value
    self.key_pbkdf2 = None

  def PreSharedKey(self):
    return self.key

  property(PreSharedKey, SetPreSharedKey, None,
           'WLANConfiguration.{i}.PreSharedKey.{i}.PreSharedKey')

  def SetKeyPassphrase(self, value):
    self.passphrase = value
    self.key = None

  def KeyPassphrase(self):
    return self.passphrase

  property(KeyPassphrase, SetKeyPassphrase, None,
           'WLANConfiguration.{i}.PreSharedKey.{i}.KeyPassphrase')

  def SetAssociatedDeviceMACAddress(self, value):
    self.assoc_mac_addr = value

  def AssociatedDeviceMACAddress(self):
    return self.assoc_mac_addr

  property(AssociatedDeviceMACAddress, SetAssociatedDeviceMACAddress, None,
           'WLANConfiguration.{i}.PreSharedKey.{i}.AssociatedDeviceMACAddress')


def main():
  pass

if __name__ == '__main__':
  main()
