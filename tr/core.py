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
# pylint: disable-msg=C6409
#
"""Base classes for TR-069 model objects.

The standard subclasses of these objects are auto-generated from the
tr-*.xml schema files and named tr???_*.py in this directory.  You can
also define nonstandard data models by extending those classes or
Exporter yourself.
"""

__author__ = 'apenwarr@google.com (Avery Pennarun)'


class NotAddableError(KeyError):
  """Raised when AddObject is not allowed on an object list."""
  pass


class SchemaError(Exception):
  """Raised when an object claims to implement a schema but doesn't."""
  pass


class AutoDict(object):
  """Class for simulating a dict that has dynamically-generated content.

  For example, a dict with a list of files in a given directory would be
  iterable (returning a list of filenames and objects corresponding to the
  filenames) and indexable (return an object given a filename) but there is
  no reason to actually cache the list of filenames; the kernel already has
  that list in real time.  So we provide a dict-like interface, and you
  can implement iteritems, getitem, setitem, etc separately.

  Use this class by either deriving from it or by just passing your own
  iteritems, getitems, etc to the constructor.  The choice depends on how
  you want to do your namespacing.
  """

  def __init__(self, name, iteritems=None,
               getitem=None, setitem=None, delitem=None):
    self.__name = name
    self.__iteritems = iteritems or self._Bad('iteritems')
    self.__getitem = getitem or self._Bad('getitem')
    self.__setitem = setitem or self._Bad('setitem')
    self.__delitem = delitem or self._Bad('delitem')

  def _Bad(self, funcname):

    # pylint: disable-msg=W0613
    def Fn(*args, **kwargs):
      raise NotImplementedError('%r must override %s'
                                % (self.__name, funcname))
    return Fn

  def iteritems(self):  # pylint: disable-msg=C6409
    return self.__iteritems()

  def __getitem__(self, key):
    return self.__getitem(key)

  def __setitem__(self, key, value):
    return self.__setitem(key, value)

  def __delitem__(self, key):
    return self.__delitem(key)

  def __contains__(self, key):
    try:
      self[key]
    except KeyError:
      return False
    return True

  def iterkeys(self):  # pylint: disable-msg=C6409
    for (k, v) in self.iteritems():  # pylint: disable-msg=W0612
      yield k

  def itervalues(self):  # pylint: disable-msg=C6409
    for (k, v) in self.iteritems():  # pylint: disable-msg=W0612
      yield v

  def __iter__(self):
    return self.iterkeys()

  def __len__(self):
    count = 0
    for i in self:  # pylint: disable-msg=W0612
      count += 1
    return count

  def keys(self):  # pylint: disable-msg=C6409
    return list(self.iterkeys())

  def values(self):  # pylint: disable-msg=C6409
    return list(self.itervalues())

  def items(self):  # pylint: disable-msg=C6409
    return list(self.iteritems())


def _Int(s):
  """Try to convert s to an int.  If we can't, just return s."""
  try:
    return int(s)
  except ValueError:
    assert '.' not in s  # dots aren't allowed in individual element names
    return s


class Exporter(object):
  """An object containing named parameters that can be get/set.

  It can also contain sub-objects with their own parameters, and attributes
  that represent lists of sub-objects.
  """

  def __init__(self, defaults=None):
    """Initialize an Exporter.

    Args:
      defaults: (optional) a dictionary of attrs to set on the object.
    """
    # Setting __lastindex = 0, means the first AddObject will have an index
    # of 1, which is what is called for in the spec.
    self.__lastindex = 0
    self.export_params = set()
    self.export_objects = set()
    self.export_object_lists = set()
    self.dirty = False  # object has pending SetParameters to be committed.
    if defaults:
      for (key, value) in defaults.iteritems():
        setattr(self, key, value)

  def Export(self, params=None, objects=None, lists=None):
    """Export some parameters, objects, or lists to make them visible.

    Once you export these, you still have to manually declare attributes
    named after the exported names.  The idea is that mostly auto-generated
    classes will call Export(), but manually-written subclasses will declare
    the actual attributes.  If you forget to declare an attribute (or you
    make a typo) then ValidateExports will fail.

    Args:
      params: a list of parameters in this object.
      objects: a list of sub-objects in this object.
      lists: a list of object-list names (lists containing objects) in this
        object.
    """
    if params:
      self.export_params.update(params)
    if objects:
      self.export_objects.update(objects)
    if lists:
      self.export_object_lists.update(lists)

  def Unexport(self, params=None, objects=None, lists=None):
    """Remove some parameters, objects, or lists to make them invisible.

    Some parameters are optional. Auto-generated classes will Export()
    all possible attributes. If an implementation chooses not to support
    some fields, it must explicitly Unexport them.

    The implementation has to deliberately choose not to implement a
    parameter, not just overlook it or skip it out of laziness.

    Args:
      params: a list of parameters to remove
      objects: a list of sub-objects to remove
      lists: a list of object-list names (lists containing objects) to remove.
    """
    if params:
      self.export_params.remove(params)
    if objects:
      self.export_objects.remove(objects)
    if lists:
      self.export_object_lists.remove(lists)

  def GetCanonicalName(self, obj_to_find):
    """Generate a canonical name for an object.

    Walk through the tree and generate the canonical name for an
    object.  The tree walk starts with this object.

    Args:
      obj_to_find: The object to generate the canonical for.
    Returns:
      The canonical path to the object.
    """
    for name in self.export_objects:
      exp_obj = self._GetExport(self, name)
      if exp_obj == obj_to_find:
        return name
      tmp_path = exp_obj.GetCanonicalName(obj_to_find)
      if tmp_path:
        return name + '.' + tmp_path

    for name in self.export_object_lists:
      objlist = self._GetExport(self, name)
      if objlist == obj_to_find:
        return name
      for (idx, child_obj) in objlist.iteritems():
        if child_obj == obj_to_find:
          return name + '.' + str(idx)
        tmp_path = child_obj.GetCanonicalName(obj_to_find)
        if tmp_path:
          return name + '.' + str(idx) + '.' + tmp_path
    return None

  def ValidateExports(self, path=None):
    """Trace through this object's exports to make no attributes are missing.

    Also goes through child objects.

    Args:
      path: (optional) a list of object name elements for use when printing
        errors, so it's easier to see which one caused the problem.

    Raises:
      SchemaError: if schema validation fails.
    """
    if not path:
      path = ['root']

    def Exc(name, msg):
      fullname = '.'.join(path + [name])
      return SchemaError('%s %s %s' % (fullname, name, msg))

    for name in self.export_params:
      self.AssertValidExport(name, path=path)
      self._GetExport(self, name)
    for name in self.export_objects:
      self.AssertValidExport(name, path=path)
      obj = self._GetExport(self, name)
      if isinstance(obj, type):
        raise Exc(name, 'is a type; instantiate it')
      try:
        obj.Export()
      except AttributeError:
        raise Exc(name, 'is %r, must implement core.Exporter'
                  % type(obj))
      obj.ValidateExports(path + [name])
    for name in self.export_object_lists:
      self.AssertValidExport(name, path=path)
      l = self._GetExport(self, name)
      try:
        for (iname, obj) in l.iteritems():  # pylint: disable-msg=W0612
          pass
      except AttributeError:
        raise Exc(name + 'List', 'is an objlist but failed to iteritems')
      for (iname, obj) in l.iteritems():
        if isinstance(obj, type):
          raise Exc('%s.%s' % (name, iname),
                    'is a type; instantiate it')
        try:
          obj.Export()
        except AttributeError:
          raise Exc(name, 'is %r, must implement core.Exporter'
                    % type(obj))
        obj.ValidateExports(path + [name])

  def IsValidExport(self, name):
    if (name in self.export_params or
        name in self.export_objects or
        name in self.export_object_lists):
      return True
    else:
      return False

  def AssertValidExport(self, name, path=None):
    if not self.IsValidExport(name):
      raise KeyError(name)
    ename = self._FixExportName(self, name)
    if not hasattr(self, ename):
      if not path:
        path = ['root']
      fullname = '.'.join(path + [ename])
      raise SchemaError('%s is exported but does not exist' % fullname)

  @staticmethod
  def _FixExportName(parent, name):
    if name in parent.export_object_lists:
      return name.replace('-', '_') + 'List'
    else:
      # Vendor models contain a dash in the domain name.
      return name.replace('-', '_')

  @staticmethod
  def _GetExport(parent, name):
    if hasattr(parent, 'IsValidExport') and not parent.IsValidExport(name):
      raise KeyError(name)
    if hasattr(parent, '_GetExport'):
      return getattr(parent, Exporter._FixExportName(parent, name))
    iname = _Int(name)
    try:
      return parent[iname]
    except KeyError:
      pass
    return parent[name]

  def FindExport(self, name, allow_create=False):
    """Navigate through the export hierarchy to find the parent of 'name'.

    Args:
      name: the name of the sub-object to find the parent of.
      allow_create: if true, try adding a row to a table to create the object.
    Returns:
      (parent, subname): the parent object and the name of the parameter or
         object referred to by 'name', relative to the parent.
    """
    parent = None
    o = self
    assert not name.endswith('.')
    parts = name.split('.')
    for i in parts[:-1]:
      parent = o
      o = self._GetExport(o, i)
    if allow_create:
      try:
        self._GetExport(o, parts[-1])
      except KeyError:
        parent.AddExportObject(parts[-2], parts[-1])
    return o, parts[-1]

  def GetExport(self, name):
    """Get a child of this object (a parameter or object).

    Args:
      name: a dot-separated sub-object name to retrieve.
    Returns:
      An Exporter instance or a parameter value.
    """
    parent, subname = self.FindExport(name)
    try:
      return self._GetExport(parent, subname)  # pylint: disable-msg=W0212
    except KeyError:
      # re-raise the KeyError with the full name, not just the subname.
      raise KeyError(name)

  def LookupExports(self, names):
    """Look up a list of export objects inside this object.

    This is like FindExport() except for a list of names instead of a
    single one, and it makes a special effort to cache objects so it doesn't
    have to walk the tree more often than necessary.

    Args:
      names: an iterable of dot-separated object names.  If a given name
        ends in '.', it is an object or a list item; if it doesn't, it is
        a parameter.
    Yields:
      a series of (obj, paramname) tuples.  For objects, paramname is
      an empty string.  Otherwise it is the last element of the dot-separated
      path, and you can do things like getattr(obj, paramname) or
      setattr(obj, paramname, 'value').  The yielded list is guaranteed
      to be in the same order as the input list of names.

      To support vendor parameters like X_CATAWAMPUS-ORG_Foo, underscores
      are substituted for dashes.
    """
    cache = {}
    cache[()] = self
    for name in names:
      if name == '.':
        name = ''
      parts = name.split('.')
      parts, param = tuple(parts[:-1]), parts[-1]
      o = self
      for i in xrange(len(parts), -1, -1):
        before, after = parts[:i], parts[i:]
        o = cache.get(before, None)
        if o is not None:
          break
      assert o is not None
      for i in after:
        before = tuple(list(before) + [i])
        cache[before] = o = Exporter._GetExport(o, i)
      yield o, param.replace('-', '_')

  def SetExportParam(self, name, value):
    """Set the value of a parameter of this object.

    Args:
      name: the parameter name to set (parameters only, not objects or lists).
      value: the value to set it to.
    Returns:
      the object modified
    Raises:
      KeyError: if the name is not an exported parameter.
    """
    parent, subname = self.FindExport(name)
    fixed = [Exporter._FixExportName(parent, x) for x in parent.export_params]
    if subname not in fixed:
      raise KeyError(name)
    if not parent.dirty:
      parent.StartTransaction()
      parent.dirty = True
    setattr(parent, subname, value)
    return parent

  def SetExportAttrs(self, param, attrs):
    """Set the attributes of a given parameter.

    Args:
      param: the parameter whose attribute is going to be set.
      attrs: dict of key/value pairs of attributes and
             the values to set.
    Returns:
      True:  If the object handled setting the attribute.
      False:  If the object does not hanlde setting the attribute.
    """
    obj, unused_name = self.FindExport(param)
    if not hasattr(obj, 'SetAttributes'):
      return False
    obj.SetAttributes(attrs)
    return True

  def _AddExportObject(self, name, idx):
    objlist = self._GetExport(self, name)
    if name not in self.export_object_lists:
      raise KeyError(name)
    try:
      constructor = getattr(self, name)
    except KeyError, e:
      raise NotAddableError('%s: %s' % (name, e))
    if idx is None:
      self.__lastindex += 1
      while str(self.__lastindex) in objlist:
        self.__lastindex += 1
      idx = self.__lastindex
    idx = str(idx)
    assert '.' not in idx
    newobj = constructor()
    try:
      newobj.ValidateExports()
    except SchemaError, e:
      raise NotAddableError('%s: %s' % (name, e))
    objlist[_Int(idx)] = newobj
    return idx, newobj

  def AddExportObject(self, name, idx=None):
    """Create a new object of type 'name' in the list self.'name'List.

    Args:
      name: the name of the object class.  The list name is self.(name+'List').
      idx: the dictionary key to store it under.  Default is auto-generated.
    Returns:
      An tuple of (idx, obj), where idx is the key and obj is the new object.
    Raises:
      KeyError: if 'name' is not an exported sub-object type.
    """
    parent, subname = self.FindExport(name)
    # pylint: disable-msg=W0212
    return parent._AddExportObject(subname, idx)

  def DeleteExportObject(self, name, idx):
    """Delete the object with index idx in the list named name.

    Args:
      name: the sub-object list to delete from.
      idx: the index of the objet to delete.
    Raises:
      KeyError: if the given index is not in the dictionary.
    """
    objlist = self.GetExport(name)
    idx = str(idx)
    try:
      if _Int(idx) in objlist:
        del objlist[_Int(idx)]
      else:
        del objlist[idx]
    except KeyError:
      raise KeyError((name, idx))

  def _ListExportsFromDict(self, objlist, recursive):
    for (idx, obj) in sorted(objlist.iteritems()):
      if obj is not None:
        yield '%s.' % (idx,)
        if recursive:
          for i in obj._ListExports(recursive):  # pylint: disable-msg=W0212
            yield '%s.%s' % (idx, i)

  def _ListExports(self, recursive):
    for name in sorted(set().union(self.export_params,
                                   self.export_objects,
                                   self.export_object_lists)):
      if name in self.export_params:
        yield name
      elif name in self.export_objects:
        yield name + '.'
        if recursive:
          obj = self._GetExport(self, name)
          # pylint: disable-msg=W0212
          for i in obj._ListExports(recursive):
            yield name + '.' + i
      if name in self.export_object_lists:
        yield name + '.'
        if recursive:
          objlist = self._GetExport(self, name)
          for i in self._ListExportsFromDict(objlist, recursive=recursive):
            yield '%s.%s' % (name, i)

  def ListExports(self, name=None, recursive=False):
    """Return a sorted list of sub-objects and parameters.

    Args:
      name: subobject name to start from (if None, starts at this object).
      recursive: true if you want to include children of children.
    Returns:
      An iterable of strings that can be passed to GetExport().
    """
    obj = self
    if name:
      obj = self.GetExport(name)
    if hasattr(obj, '_ListExports'):
      # pylint: disable-msg=W0212
      return obj._ListExports(recursive=recursive)
    else:
      return self._ListExportsFromDict(obj, recursive=recursive)

  def StartTransaction(self):
    """Prepare for a series of Set operations, to be applied atomically.

    After StartTransaction the object will receive zero or more set operations
    to its exported parameters. Each Set should check its arguments as best it
    can, and raise ValueError or TypeError if there is a problem.

    The transaction will conclude with either an AbandonTransaction or
    CommitTransaction.
    """
    pass

  def AbandonTransaction(self):
    """Discard a pending transaction; do not apply the changes to the system."""
    pass

  def CommitTransaction(self):
    """Apply a pending modification to the system."""
    pass


class TODO(Exporter):
  """Use this class to fake out an Exporter instance.

  Useful when you're implementing a big TR-069 Model hierarchy and you don't
  want to implement every single class right now.  As a bonus, it'll show up
  when you grep for TODO in the source code.
  """

  def __init__(self):
    Exporter.__init__(self)
    self.Export(params=['TODO'])
    self.TODO = 'CLASS NOT IMPLEMENTED YET'


def Dump(root):
  """Return a string representing the contents of an object.

  This function works only if root.ValidateExports() would pass.

  Args:
    root: the object to dump.
  Returns:
    A big string containing lines of the format:
      Object.SubObject.
      Object.SubObject.ParameterName = %r
  """
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
  elif hasattr(root, '__call__') and not hasattr(root, 'export_params'):
    root = root()
  for i in root.export_params:
    name = i.replace('-', '_')
    out.append('.'.join(path + [name]))
  for i in root.export_objects:
    name = i.replace('-', '_')
    out.append('.'.join(path + [name, '']))
    _DumpSchema(getattr(root, name), out, path + [name])
  for i in root.export_object_lists:
    name = i.replace('-', '_')
    out.append('.'.join(path + [name, '']))
    out.append('.'.join(path + [name, '{i}']))
    _DumpSchema(getattr(root, name), out, path + [name, '{i}'])


def DumpSchema(root):
  """Return a string representing the object model implemented by the object.

  You can use this to show which objects, sub-objects, and parameters *should*
  be implemented by an object, even if that object isn't fully implemented
  yet by adding the right attrs in a subclass.  This is useful for figuring
  out which attrs you *need* to add in a subclass.  Auto-generated tr*.py
  files run this automatically when you execute them from the command line.

  This function works even if root.ValidateExports() would fail.

  Args:
    root: the object or type to dump.  If a type, instantiates it.
  Returns:
    A big string of the format:
      Object.SubObject.
      Object.SubObject.ParameterName
  """
  out = []
  if isinstance(root, type):
    root = root()
  _DumpSchema(root, out, [root.__class__.__name__])
  return '\n'.join(sorted(out))


class ResourcesExceededError(BufferError):
  """Exception to send a RESOURCES_EXCEEDED SOAP:Fault."""
  pass


class FileTransferProtocolError(NotImplementedError):
  """Exception to send a FILE_TRANSFER_PROTOCOL SOAP:Fault."""
  pass


class CancelNotPermitted(Exception):
  """Exception to send a DOWNLOAD_CANCEL_NOTPERMITTED SOAP:Fault."""
  pass
