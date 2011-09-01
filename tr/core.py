#!/usr/bin/python
# Copyright 2011 Google Inc. All Rights Reserved.
#
"""Base classes for TR-069 model objects.

The standard subclasses of these objects are auto-generated from the
tr-*.xml schema files and dropped into the std/ subdirectory.  You can
also define nonstandard data models by extending those classes or
Exporter yourself.
"""

__author__ = 'apenwarr@google.com (Avery Pennarun)'


_lastindex = -1


class NotAddableError(KeyError):
    pass


class SchemaError(Exception):
    pass


class Exporter(object):
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

  def ValidateExports(self, path=None):
    if not path:
      path = ['root']
    def Exc(name, msg):
      fullname = '.'.join(path+[name])
      return SchemaError('%s %s' % (fullname, msg))
    for name in self.export_params:
        try:
            self._GetExport(name)
        except AttributeError:
            raise Exc(name, 'is a param but does not exist')
    for name in self.export_objects:
        try:
            obj = self._GetExport(name)
        except KeyError:
            raise Exc(name, 'is an obj but does not exist')
        if isinstance(obj, type):
            raise Exc(name, 'is a type; instantiate it')
        try:
            obj.Export()
        except AttributeError:
            raise Exc(name, 'is %r, must implement core.Exporter'
                      % type(obj))
        obj.ValidateExports(path+[name])
    for name in self.export_object_lists:
        try:
            l = self._GetExport(name)
        except KeyError:
            raise Exc(name, 'is an objlist but does not exist')
        try:
            for iname,obj in l.iteritems():
                pass
        except TypeError:
            raise Exc(name + 'List', 'is an objlist but failed to iteritems')
        for iname,obj in l.iteritems():
            if isinstance(obj, type):
                raise Exc('%s.%s' % (name, iname),
                          'is a type; instantiate it')
            try:
                obj.Export()
            except AttributeError:
                raise Exc(name, 'is %r, must implement core.Exporter'
                          % type(obj))
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
    return idx,newobj

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
    if recursive:
        self.ValidateExports()
    return list(sorted(self._ListExports(recursive=recursive)))


class TODO(Exporter):
    def __init__(self):
        Exporter.__init__(self)
        self.Export(params=['TODO'])
        self.TODO = 'CLASS NOT IMPLEMENTED YET'


def Dump(root):
    out = []
    for i in root.ListExports(recursive=True):
        if i.endswith('.'):
            out.append('  %s' % (i,))
        else:
            out.append('  %s = %r' % (i, root.GetExport(i)))
    return '\n'.join(out)


def _DumpSchema(root, out, path):
    if isinstance(root, type):
        root = root()
    for i in root.export_params:
        out.append('.'.join(path + [i]))
    for i in root.export_objects:
        out.append('.'.join(path + [i, '']))
        _DumpSchema(getattr(root, i), out, path + [i])
    for i in root.export_object_lists:
        out.append('.'.join(path + [i, '']))
        out.append('.'.join(path + [i, '{i}']))
        _DumpSchema(getattr(root, i), out, path + [i, '{i}'])


def DumpSchema(root):
    out = []
    if isinstance(root, type):
        root = root()
    _DumpSchema(root, out, [root.__class__.__name__])
    return '\n'.join(sorted(out))
