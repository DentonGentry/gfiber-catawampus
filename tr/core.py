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
"""Base classes for TR-069 model objects.

The standard subclasses of these objects are auto-generated from the
tr-*.xml schema files and named tr???_*.py in this directory.  You can
also define nonstandard data models by extending those classes or
Exporter yourself.

For navigating the tree, look at handle.Handle().
"""

__author__ = 'apenwarr@google.com (Avery Pennarun)'


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
    if getitem:
      self.__getitem = getitem
    elif iteritems:
      self.__getitem = self._GetItemFromIterItems
    else:
      self.__getitem = self._Bad('getitem')
    self.__setitem = setitem or self._Bad('setitem')
    self.__delitem = delitem or self._Bad('delitem')

  def _Bad(self, funcname):

    # pylint:disable=unused-argument
    def Fn(*args, **kwargs):
      raise NotImplementedError('%r must override %s'
                                % (self.__name, funcname))
    return Fn

  def _GetItemFromIterItems(self, key):
    for (k, v) in self.iteritems():
      if k == key:
        return v
    raise KeyError(key)

  def iteritems(self):
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

  def iterkeys(self):
    for (k, _) in self.iteritems():
      yield k

  def itervalues(self):
    for (_, v) in self.iteritems():
      yield v

  def __iter__(self):
    return self.iterkeys()

  def __len__(self):
    count = 0
    for _ in self:
      count += 1
    return count

  def keys(self):
    return list(self.iterkeys())

  def values(self):
    return list(self.itervalues())

  def items(self):
    return list(self.iteritems())


class AbstractExporter(object):
  """A basic data model.  Most implementations derive from Exporter."""

  # No per-instance variables.  Define a subclass if you need some.
  __slots__ = ()

  # The following members might be overridden as properties or per-instance
  # objects in subclasses.  We don't assign them in __init__ because that
  # would prevent subclasses from making them properties.

  # Setting _lastindex = 0, means the first AddObject will have an index
  # of 1, which is what is called for in the spec.
  _lastindex = 0
  dirty = False  # true if object has pending SetParameters to be committed
  export_params = ()
  export_objects = ()
  export_object_lists = ()

  def __init__(self):
    pass

  def Export(self, params=None, objects=None, lists=None):
    raise NotImplementedError()

  def Unexport(self, params=None, objects=None, lists=None):
    raise NotImplementedError()

  def Close(self):
    """Called when an object is being deleted."""
    pass

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


class FastExporter(AbstractExporter):
  """An object containing named parameters that can be get/set.

  It can also contain sub-objects with their own parameters, and attributes
  that represent lists of sub-objects.
  """

  __slots__ = (
      '_Attr__Attrs',  # for tr.cwmptypes magic
      'dirty',         # for transactions
  )

  def __init__(self, **defaults):
    """Initialize an Exporter.

    Args:
      **defaults: (optional) a dictionary of attrs to set on the object.
    """
    super(FastExporter, self).__init__()
    self.dirty = False
    for (key, value) in defaults.iteritems():
      setattr(self, key, value)

  def Export(self, params=None, objects=None, lists=None):
    """Deprecated.  Use @tr.core.Exports() on the class instead."""
    Exports(params, objects, lists)(self)

  def Unexport(self, params=None, objects=None, lists=None):
    """Deprecated.  Use @tr.core.Unexports() on the class instead."""
    Unexports(params, objects, lists)(self)


class Exporter(FastExporter):
  """Exactly like FastExporter, but runtime extensible (no __slots__)."""
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


def Exports(params=None, objects=None, lists=None):
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

  Returns:
    A function that takes an object or class as a parameter, and returns
    that same object with its export_* members possibly appended to.

  Example:
    @Exports(params=['Foo'])
    class MyClass(Exporter):
      ...
  """
  assert not isinstance(params, basestring)
  assert not isinstance(objects, basestring)
  assert not isinstance(lists, basestring)
  def Wrapper(obj):
    if params:
      obj.export_params = tuple(set(obj.export_params) | set(params))
    if objects:
      obj.export_objects = tuple(set(obj.export_objects) | set(objects))
    if lists:
      obj.export_object_lists = tuple(set(obj.export_object_lists) | set(lists))
    return obj
  return Wrapper


def Unexports(params=None, objects=None, lists=None):
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

  Returns:
    A function that takes an object or class as a parameter, and returns
    that same object with its export_* members possibly reduced.

  Example:
    @Unexports(params=['Foo'])
    class MyClass(Exporter):
      ...
  """
  def Wrapper(obj):
    if params:
      obj.export_params = tuple(set(obj.export_params) - set(params))
    if objects:
      assert not isinstance(objects, basestring)
      obj.export_objects = tuple(set(obj.export_objects) - set(objects))
    if lists:
      assert not isinstance(lists, basestring)
      obj.export_object_lists = tuple(set(obj.export_object_lists) - set(lists))
    return obj
  return Wrapper


def Extensible(cls):
  """Returns a subclass of cls that has no __slots__ member.

  This allows you to set arbitrary members in each instance, even if they
  don't exist already in the class.

  This is useful for making one-off Exporter() instances in tests,
  for example.

  Args:
    cls: a class to inherit from.

  Returns:
    A new class derived from cls.

  Example:
    o = Extensible(object)
    o.Foo = 5
  """

  class Ext(cls):
    pass

  Ext.__name__ = 'Ext_' + cls.__name__
  return Ext


class ResourcesExceededError(BufferError):
  """Exception to send a RESOURCES_EXCEEDED SOAP:Fault."""
  pass


class FileTransferProtocolError(NotImplementedError):
  """Exception to send a FILE_TRANSFER_PROTOCOL SOAP:Fault."""
  pass


class CancelNotPermitted(Exception):
  """Exception to send a DOWNLOAD_CANCEL_NOTPERMITTED SOAP:Fault."""
  pass
