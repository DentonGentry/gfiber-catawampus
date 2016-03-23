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
"""Implement logging for cwmpd."""


import os
import xml.etree.cElementTree as ET


SUPPRESSLIST = frozenset(['ParameterNames', 'string', 'ParameterList',
                          'ParameterValueStruct', 'DeviceId', 'Event',
                          'EventStruct', 'detail', 'Header', 'Body',
                          'SetParameterAttributesStruct'])
PRUNELIST = frozenset(['MaxEnvelopes', 'ParameterKey', 'CommandKey',
                       'Manufacturer', 'OUI', 'ProductClass',
                       'HoldRequests'])
TRUNCATELIST = frozenset(['GetParameterValues', 'GetParameterValuesResponse',
                          'GetParameterNamesResponse', 'SetParameterAttributes',
                          'X_CATAWAMPUS_ORG_AddObjects',
                          'X_CATAWAMPUS_ORG_AddObjectsResponse'])


def _Shorten(s, prefixofs, suffixofs, maxlen):
  """Shorten the given string if its length is >= maxlen.

  Note: maxlen should generally be considerably bigger than
  prefixofs + suffixofs.  It's disconcerting to a reader when
  you have a "..." to replace 10 bytes, but it feels fine when the
  "..." replaces 500 bytes.

  Args:
    s: the string to shorten.
    prefixofs: the number of chars to keep at the beginning of s.
    suffixofs: the number of chars to keep at the end of s.
    maxlen: if the string is longer than this, shorten it.
  Returns:
    A shortened version of the string.
  """
  s = str(s)
  if len(s) >= maxlen:
    # When the string exceeds the limit, we deliberately shorten it to
    # considerably less than the limit, because it's disconcerting when
    # you have a "..." to replace 10 bytes, but it feels right when the
    # "..." replaces 500 bytes.
    s = s[0:prefixofs] + '.....' + s[-suffixofs:]
  return s


def _StripNamespace(tag):
  """Remove Namespace from XML Tag.

  ElementTree retains namespaces in the tag, like:
  {urn:dslforum-org:cwmp-1-2}GetParameterNames
  The namespace is not useful; suppress it.

  Args:
    tag: the tag name
  Returns:
    the tag with namespace removed, if there was one.
  """
  if tag[0] == '{':
    e = tag.find('}')
    return tag[e + 1:]
  else:
    return tag


def _SuppressSensitiveParams(name, value):
  """Don't log passwords, and other sensitive information."""
  if 'KeyPassphrase' in name or 'WEPKey' in name or 'Password' in name:
    value = 'XXXXXXXX'
  return (name, value)


def _LogSoapETree(et, prefix=''):
  """Tersely log an ElementTree CWMP message.

  Example output:

  ID: google.acs.1370212049608.571675
  SetParameterValues:
    InternetGatewayDevice.ManagementServer.PeriodicInformEnable = true
    InternetGatewayDevice.ManagementServer.PeriodicInformInterval = 60

  Args:
    et: an ElementTree node
    prefix: a string to prepend to each line (generally indentation)
  Returns:
    the string to log.
  """
  if len(et) == 2 and et[0].tag == 'Name' and et[1].tag == 'Value':
    # change:
    #   Name: InternetGatewayDevice.Foo.Bar
    #   Value: 60
    # to:
    #   InternetGatewayDevice.Foo.Bar = 60
    text0 = et[0].text and et[0].text.strip()
    name = _Shorten(text0, 8, 32, 64)
    text1 = et[1].text and et[1].text.strip()
    value = _Shorten(text1, 16, 64, 192)
    (name, value) = _SuppressSensitiveParams(name, value)
    return '%s%s = %s\n' % (prefix, name, value)
  if et.text and et.text.strip():
    return '%s%s\n' % (prefix, et.text.strip())
  out = ''
  for child in et:
    tag = _StripNamespace(child.tag)
    if tag in PRUNELIST:
      et.remove(child)
      continue
    if tag in SUPPRESSLIST:
      out += '%s' % _LogSoapETree(child, prefix)
    elif child.text and child.text.strip():
      # Child is a leaf node; all on one line
      out += '%s%s: %s\n' % (prefix, tag, child.text.strip())
    else:
      body = _LogSoapETree(child, prefix + '  ')
      if tag in TRUNCATELIST:
        lines = body.splitlines()
        numlines = len(lines)
        if numlines > 8:
          lines = lines[0:3]
          lines.append('%s...%d more lines...' % (prefix + '  ', numlines - 3))
          body = '\n'.join(lines)
      out += '%s%s:\n%s' % (prefix, tag, body)
  return out


class Logger(object):
  """CWMP-specific logging support.

  This class logs XML logs for the first few sessions after
  reboot, trying to capture the initial GetParameterValues
  exchanges and an AddObject or two. Then it switches to a
  much more condensed logging format.
  """

  def __init__(self, full_logs=10):
    self.num_full_logs = full_logs

  def LogSoapXML(self, xml):
    if not xml or not xml.strip():
      # An empty message is valid, means connection is closing.
      return ''

    # Developers can ask for full XML logs.
    if os.environ.get('DONT_SHORTEN'):
      return str(xml)

    if self.num_full_logs > 0:
      self.num_full_logs -= 1
      return self.LogXML(xml)
    else:
      return self.LogTerse(xml)

  def LogXML(self, xml):
    return _Shorten(str(xml), 1024, 512, 3072)

  def LogTerse(self, xml):
    try:
      return _LogSoapETree(ET.fromstring(xml))
    except:  # Never, ever kill catawampus for this. pylint:disable=bare-except
      print 'Unable to parse XML for logging.'
      return str(xml)
