#!/usr/bin/python
# Copyright 2011 Google Inc. All Rights Reserved.
#
"""Base classes for TR-069 model objects.

The standard subclasses of these objects are auto-generated from the
tr-*.xml schema files and dropped into the std/ subdirectory.  You can
also define nonstandard data models by extending those classes or
ParameterizedObject yourself.
"""

__author__ = 'apenwarr@google.com (Avery Pennarun)'


_objects = {}
_last_index = 0


def _NextIndex():
  global _last_index
  _last_index += 1
  return _last_index


class ParameterizedObject(object):
  """An object containing named parameters that can be get/set."""

  def __init__(self, name_prefix, params=None, **kwargs):
    assert name_prefix.endswith('.')
    self.index = _NextIndex()
    self.name = '%s%d' % (name_prefix, self.index)
    self.params = params or {}
    self.params.update(kwargs)
    _objects[self.name] = self

  def __repr__(self):
    return '%s%r' % (self.name, self.params)

  def GetParam(self, name):
    return self.params[name]

  def SetParam(self, name, value):
    self.params[name]  # make sure it already exists
    self.params[name] = value

  def ListParams(self):
    return list(sorted(self.params.keys()))
