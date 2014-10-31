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
"""A wrapper for accessing a tree of core.Exporter objects."""


class NotAddableError(KeyError):
  """Raised when AddObject is not allowed on an object list."""
  pass


class SchemaError(Exception):
  """Raised when an object claims to implement a schema but doesn't."""
  pass


def _Int(s):
  """Try to convert s to an int.  If we can't, just return s."""
  try:
    return int(s)
  except ValueError:
    assert '.' not in s  # dots aren't allowed in individual element names
    return s


def ValidateExports(obj, path=None):
  """Shortcut for creating and validating a handle."""
  return Handle(obj).ValidateExports(path=path)


class Handle(object):
  """A wrapper for accessing a tree of core.Exporter objects.

  By using a Handle object for accessing the tree, we can keep all the
  traversal logic out of the Exporter API.  When accessing an Exporter
  object directly, you can use normal python names (Obj.ThingList[5].Name),
  and when accessing via a Handle, you use TR-069 names
  ('Obj.ThingList.5.Name').
  """

  def __init__(self, obj):
    assert hasattr(obj, 'Export') or hasattr(obj, 'iteritems')
    self.obj = obj

  def SubHandle(self, obj):
    return type(self)(obj)

  @staticmethod
  def GetCanonicalName(root, obj_to_find):
    """Generate a canonical name for an object.

    Walk through the tree and generate the canonical name for an
    object.  The tree walk starts with this object.

    WARNING: This function is horribly slow! It really does visit every node
    in the whole tree, even virtual ones, while looking for obj_to_find.
    It's also possible that the object you're looking for is virtual and
    is no longer in the tree (or has been replaced) by the time we try to
    visit it, in which case it won't have a canonical name at all.

    Args:
      root: the object to start searching from.
      obj_to_find: The object to generate the canonical for.
    Returns:
      The canonical path to the object.
    """
    for name in root.export_objects:
      exp_obj = Handle._GetExport(root, name)
      if exp_obj == obj_to_find:
        return name
      tmp_path = Handle.GetCanonicalName(exp_obj, obj_to_find)
      if tmp_path:
        return name + '.' + tmp_path

    for name in root.export_object_lists:
      objlist = Handle._GetExport(root, name)
      if objlist == obj_to_find:
        return name
      for (idx, child_obj) in objlist.iteritems():
        if child_obj == obj_to_find:
          return name + '.' + str(idx)
        tmp_path = Handle.GetCanonicalName(child_obj, obj_to_find)
        if tmp_path:
          return name + '.' + str(idx) + '.' + tmp_path
    return None

  def ValidateExports(self, path=None):
    """Trace through this object's exports to ensure no attributes are missing.

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

    for name in self.obj.export_params:
      self.AssertValidExport(name, path=path)
      self._GetExport(self.obj, name)
    for name in self.obj.export_objects:
      self.AssertValidExport(name, path=path)
      obj = self._GetExport(self.obj, name)
      if isinstance(obj, type):
        raise Exc(name, 'is a type; instantiate it')
      try:
        obj.Export()
      except AttributeError:
        raise Exc(name, 'is %r, must implement core.Exporter'
                  % type(obj))
      self.SubHandle(obj).ValidateExports(path + [name])
    for name in self.obj.export_object_lists:
      self.AssertValidExport(name, path=path)

      l = self._GetExport(self.obj, name)
      items = list(l.iteritems())
      try:
        if getattr(self, name + 'NumberOfEntries') != len(items):
          raise Exc(name + 'NumberOfEntries', 'does not match len(%s)' % name)
      except AttributeError:
        # no NumberOfEntries element; that's allowed
        pass

      try:
        for (unused_iname, unused_obj) in l.iteritems():
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
        self.SubHandle(obj).ValidateExports(path + [name, str(iname)])

  @staticmethod
  def IsValidExport(obj, name):
    if (name in obj.export_params or
        name in obj.export_objects or
        name in obj.export_object_lists):
      return True
    else:
      return False

  def AssertValidExport(self, name, path=None):
    if not self.IsValidExport(self.obj, name):
      raise KeyError(name)
    ename = self._FixExportName(self.obj, name)
    if not hasattr(self.obj, ename):
      if not path:
        path = ['root']
      fullname = '.'.join(path + [ename])
      try:
        # hasattr() just eats all exceptions and returns false, even if
        # it wasn't the correct AttributeError, which is hard to debug.
        # So we getattr() if not hasattr(); getattr() will raise the real
        # exception, which we deliberately allow to percolate out.
        getattr(self.obj, ename)
      except AttributeError, e:
        # AttributeError probably means the attribute actually doesn't exist.
        # There's one exception to that: running an @property might
        # accidentally throw AttributeError for some other reason.  Just in
        # case, we print the original exception string in addition to our
        # SchemaError.
        raise SchemaError('%s is exported but does not exist (%s)'
                          % (fullname, e))

  @staticmethod
  def _FixExportName(parent, name):
    if name in parent.export_object_lists:
      return name.replace('-', '_') + 'List'
    else:
      # Vendor models contain a dash in the domain name.
      return name.replace('-', '_')

  @staticmethod
  def _GetExport(parent, name):
    """Find an export called 'name' that is directly under object 'parent'."""
    if hasattr(parent, 'Export'):
      if not Handle.IsValidExport(parent, name):
        raise KeyError(name)
      else:
        return getattr(parent, Handle._FixExportName(parent, name))
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
    o = self.obj
    assert not name.endswith('.')
    parts = name.split('.')
    for i in parts[:-1]:
      parent = o
      o = self._GetExport(o, i)
    if allow_create:
      try:
        self._GetExport(o, parts[-1])
      except KeyError:
        self.SubHandle(parent).AddExportObject(parts[-2], parts[-1])
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
      return self._GetExport(parent, subname)
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
        cache[before] = o = self.SubHandle(Handle._GetExport(o.obj, i))
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
    fixed = [Handle._FixExportName(parent, x) for x in parent.export_params]
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
    """Same as AddExportObject, but 'name' must be a direct child (no dots)."""
    objlist = self._GetExport(self.obj, name)
    if name not in self.obj.export_object_lists:
      raise KeyError(name)
    try:
      constructor = getattr(self.obj, name)
    except KeyError, e:
      raise NotAddableError('%s: %s' % (name, e))
    # pylint:disable=protected-access
    if idx is None:
      self.obj._lastindex += 1
      while str(self.obj._lastindex) in objlist:
        self.obj._lastindex += 1
      idx = self.obj._lastindex
    # pylint:enable=protected-access
    idx = str(idx)
    assert '.' not in idx
    newobj = constructor()
    try:
      self.SubHandle(newobj).ValidateExports()
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
    # pylint:disable=protected-access
    return self.SubHandle(parent)._AddExportObject(subname, idx)

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
      obj = None
      if _Int(idx) in objlist:
        obj = objlist[_Int(idx)]
        obj.Close()
        del objlist[_Int(idx)]
      else:
        obj = objlist[idx]
        obj.Close()
        del objlist[idx]
    except KeyError:
      raise KeyError((name, idx))

  def _ListExportsFromDict(self, objlist, recursive):
    if not hasattr(objlist, 'iteritems'):
      return
    for (idx, obj) in sorted(objlist.iteritems()):
      if obj is not None:
        yield '%s.' % (idx,)
        if recursive:
          for i in self.SubHandle(obj)._ListExports(recursive):  # pylint:disable=protected-access
            yield '%s.%s' % (idx, i)

  def _ListExports(self, recursive):
    for name in sorted(set().union(self.obj.export_params,
                                   self.obj.export_objects,
                                   self.obj.export_object_lists)):
      if name in self.obj.export_params:
        yield name
      elif name in self.obj.export_objects:
        yield name + '.'
        if recursive:
          obj = self._GetExport(self.obj, name)
          # pylint:disable=protected-access
          for i in self.SubHandle(obj)._ListExports(recursive):
            yield name + '.' + i
      if name in self.obj.export_object_lists:
        yield name + '.'
        if recursive:
          objlist = self._GetExport(self.obj, name)
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
    obj = self.obj
    if name:
      obj = self.GetExport(name)
    if hasattr(obj, 'Export'):
      # pylint:disable=protected-access
      return self.SubHandle(obj)._ListExports(recursive=recursive)
    else:
      return self._ListExportsFromDict(obj, recursive=recursive)


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
  h = Handle(root)
  out = []
  for i in h.ListExports(recursive=True):
    if i.endswith('.'):
      out.append('  %s' % (i,))
    else:
      out.append('  %s = %r' % (i, h.GetExport(i)))
  return '\n'.join(out)


def _DumpSchema(root, out, path):
  """Helper function for DumpSchema()."""
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
    A big multi-line string of the format:
      Object.SubObject.
      Object.SubObject.ParameterName
      ...etc...
  """
  out = []
  if isinstance(root, type):
    root = root()
  _DumpSchema(root, out, [root.__class__.__name__])
  return '\n'.join(sorted(out))