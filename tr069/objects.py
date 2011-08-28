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


_lastindex = -1


class NotAddableError(KeyError):
    pass


class ParameterizedObject(object):
  """An object containing named parameters that can be get/set.

  It can also contain sub-objects with their own parameters, and attributes
  that represent lists of sub-objects.
  """

  def __init__(self):
    self.export_params = set()
    self.export_objects = set()
    self.export_object_lists = set()

  def Export(self, params=None, objects=None, lists=None):
    if params:
        self.export_params.update(params)
    if objects:
        self.export_objects.update(objects)
    if lists:
        self.export_object_lists.update(lists)

  def ValidateExports(self):
    for name in self.export_params:
        self._GetExport(name)
    for name in self.export_objects:
        obj = self._GetExport(name)
        assert isinstance(obj, ParameterizedObject)
        obj.ValidateExports()
    for name in self.export_object_lists:
        l = self._GetExport(name)
        for obj in l:
            assert isinstance(obj, ParameterizedObject)
            obj.ValidateExports()
            
  def AssertValidExport(self, name):
    if (name not in self.export_params and
        name not in self.export_objects and
        name not in self.export_object_lists):
      raise KeyError(name)

  def _GetExport(self, name):
    self.AssertValidExport(name)
    if name in self.export_object_lists:
        return getattr(self, name + 'List')
    else:
        return getattr(self, name)

  def GetExport(self, name):
      o = self
      assert(not name.endswith('.'))
      for i in name.split('.'):
          if hasattr(o, '_GetExport'):
              o = o._GetExport(i)
          else:
              o = o[i]
      return o

  def SetExportParam(self, name, value):
    if name not in self.export_params:
        raise KeyError(name)
    setattr(self, name, value)

  def AddExportObject(self, name, idx=None):
    objlist = self._GetExport(name)
    if name not in self.export_object_lists:
        raise KeyError(name)
    try:
        constructor = getattr(self, name)
    except KeyError:
        raise NotAddableError(name)
    if idx is None:
        global _lastindex
        _lastindex += 1
        while _lastindex in objlist:
            _lastindex += 1
        idx = _lastindex
    idx = str(idx)
    assert '.' not in idx
    newobj = constructor()
    objlist[idx] = newobj
    return newobj

  def DeleteExportObject(self, name, idx):
    idx = str(idx)
    objlist = self._GetExport(name)
    if idx not in objlist:
        raise KeyError((name,idx))
    del objlist[idx]

  def _ListExports(self, recursive=False):
    for name in self.export_params:
        yield name
    for name in self.export_objects:
        yield name + '.'
        if recursive:
            obj = self._GetExport(name)
            for i in obj._ListExports(recursive):
                yield name + '.' + i
    for name in self.export_object_lists:
        yield name + '.'
        if recursive:
            objlist = self._GetExport(name)
            for idx,obj in objlist.iteritems():
                if obj is not None:
                    for i in obj._ListExports(recursive):
                        yield '%s.%s.%s' % (name, idx, i)

  def ListExports(self, recursive=False):
    return list(sorted(self._ListExports(recursive=recursive)))


def Dump(root):
    out = []
    for i in root.ListExports(recursive=True):
        if i.endswith('.'):
            out.append('  %s' % (i,))
        else:
            out.append('  %s = %r' % (i, root.GetExport(i)))
    return '\n'.join(out)
