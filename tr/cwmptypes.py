#!/usr/bin/python
# Copyright 2012 Google Inc. All Rights Reserved.
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
# pylint: disable=invalid-name
#
"""Type descriptors for common TR-069 data types."""

__author__ = 'apenwarr@google.com (Avery Pennarun)'

import datetime
import errno
import os
import re
import socket
import weakref
import cwmpdate
import helpers
import mainloop


MACADDR_REGEX = re.compile(r"""(^([0-9A-F]{2}[-]){5}([0-9A-F]{2})$
                                   |^([0-9A-F]{2}[:]){5}([0-9A-F]{2})$
                                   )""", re.VERBOSE | re.IGNORECASE)


class Attr(object):
  """A descriptor that holds an arbitrary attribute.

  This isn't very useful on its own, but we declare type-specific child
  classes that enforce the data type.  For example:

    class X(object):
      a = Attr()
      b = Bool()
      s = String()
      i = Int()
      e = Enum('Bob', 'Fred')
    x = X()
    x.a = object()
    x.b = '0'    # actually gets set to integer 0
    x.s = [1,2]  # gets set to the string unicode([1, 2])
    x.i = '9'    # auto-converts to a real int
    x.e = 'Stinky'  # raises exception since it's not an allowed value

  The way this works is when the class is instantiated, python treats
  'descriptor' members (basically anything with a __get__ or __set__)
  specially, calling the __get__ or __set__ function whenever you try to
  read or write the member.  @property is just one default kind of descriptor;
  we're defining a series of other ones here, which mostly enforce type
  safety but have a couple of extra features (like notifier callbacks).

  Storage of per-instance values for descriptors is very strange.  The problem
  (although it's essential that it works this way) is that a descriptor
  instance is created for the *class*, not for each instance of that class.
  Thus, we have to manage our own storage.

  cwmptypes.Attr used to handle this by adding an __Attr dict to each
  instance, and storing the values of each Attr in there.  This worked,
  but it turned out we wanted to create a *lot* of objects containing
  attrs (eg. periodic_statistics.py) and the extra dict was too expensive.
  (Note: storage inside the Attr instance is pretty cheap, because only one
  instance is ever made per Attr declaration.  But storage per instance of
  the class *containing* the Attr is expensive.)

  So instead, we now have to do an extra layer of magic:
   - discover the name of this Attr by looking at the class it's declared
     in (see _MyAttrName)
   - store the value itself in a second property named _Name, where Name
     is the name discovered above.  (There's no need to ever access _Name
     directly; access it through the Attr instead.)

  This method gets further confused when you wrap an Attr in another
  kind of descriptor (like Trigger, ReadOnly, etc, defined below).  When
  that happens, we still need to find which property name maps to this Attr,
  but this Attr doesn't appear directly in the containing object.  That's why
  we need SetWrapper and _outermost; we use that to coordinate across a chain
  of Attr and Attr-wrappers so they can find which class they're actually
  instantiated inside, so they can find their name, so they can figure out
  where to store their value.
  """

  def __init__(self, init=None):
    self.init = init
    self._callbacklist = []
    self._attrname = None
    self._outermost = self

  @property
  def callbacklist(self):
    """The callbacklist is read-only, but you can change its contents."""
    return self._callbacklist

  def SetWrapper(self, wrapattr):
    """Tell this Attr that another is wrapping it, eg. Trigger or ReadOnly."""
    self._outermost = wrapattr

  def _MyAttrName(self, obj):
    """Return the attr name we'll store this property's value in.

    Args:
      obj: an instance object containing this property.
    Returns:
      a string to identify this property's value.  For example, if a class
      is declared with:
        MyProp = ReadOnly(Unsigned(0))
      then this function will return '_MyProp' if self is the ReadOnly or
      Unsigned object and obj is an instance of the declared class.
    Raises:
      Exception: if this attribute is somehow not in 'obj'.  (Should never
        happen unless there's a bug in cwmptypes.)
    """
    assert obj
    if not self._attrname:
      # It would be nice to use type(obj).__dict__.iteritems() here, but
      # unfortunately that doesn't see members in any parent classes' dicts.
      cls = type(obj)
      for k in dir(cls):
        if getattr(cls, k) == self._outermost:
          self._attrname = '_' + k
          break
      if not self._attrname:
        raise Exception('attribute %r is not in object %r' % (self, obj))
    return self._attrname

  def _SetInstanceAttr(self, obj, value):
    setattr(obj, self._MyAttrName(obj), value)

  def _GetInstanceAttr(self, obj):
    return getattr(obj, self._MyAttrName(obj))

  def __get__(self, obj, _):
    # Type descriptors (ie. this class) are weird because they only have
    # one instance per member of a class, not per member of an *object*.
    # That is, all the objects of a given class share the same type
    # descriptor instance.  Thus, we have to store the actual property
    # value in a hidden variable in each obj, rather than in self.
    if obj is None:
      return self
    try:
      return self._GetInstanceAttr(obj)
    except AttributeError:
      if self.init is None:
        # special case: if init==None, don't do consistency checking, in
        # order to support initially-invalid variables
        self._SetWithoutNotify(obj, None)
      else:
        self._SetWithoutNotify(obj, self.validate(obj, self.init))
      return self._GetInstanceAttr(obj)

  def validate(self, obj, value):  # pylint: disable=unused-argument
    """Validate or convert a potential new value for this attribute.

    Callers can check this function to see if the attribute *could* be
    assigned a particular value, or if it were, what it would be converted
    into, without actually setting the value (and thus triggering any
    side effects of setting the attribute).  This is useful when implementing
    simple transactions, because you can test each variable first to see if
    it *could* be set to a particular value, and only if all of them can,
    continue with the transaction.  The default validator just allows all
    values.

    Note: normally you will call the global tryattr() function, which calls
    this for you.

    Note2: This base class's validator just accepts any value and will always
    do so.  You don't need to call the superclass's version if you override
    it in a derived class.

    Args:
      obj: the object owning the attribute.
      value: the value to test.
    Returns:
      value or a modified value (eg. typecast into a different type)
    Raises:
      Any exception.
    """
    # default implementation allows any value
    return value

  def validator(self, valfunc):
    """An @wrapper for adding a level of validation to the current property.

    Both the input *and* the output of the validator function are passed
    through the pre-existing validator chain.  That is, if you add a
    validator to an Int() object, the input to your function will already
    be coerced to int (or rejected if it can't be converted to an int, in
    which case your function is never called).  Then, the value returned by
    your function will also be coerced to an int on the way out.  This makes
    it easy to write type-safe functions.

    You can safely use @x.validator more than once on a given property x,
    and it will add a new level of validation each time.  Probably that
    isn't actually useful however.

    Example usage:
      class X(object):
        i = Int()
        @i.validator
        def i(self, value):
          if i < 0:
            raise ValueError('i must be >= 0')
          elif i > 100:
            return 100
          else:
            return i * 2.5

      x = X()
      x.i = 9.3
      print x.i   # prints int(int(9.3) * 2.5) == 22

    Args:
      valfunc: a function(obj, value) that returns a validated value.
    Returns:
      A new type descriptor that validates when you try to set the value.
    """
    old_valfunc = self.validate

    def fn(obj, value):
      return old_valfunc(obj, valfunc(obj, old_valfunc(obj, value)))
    self.validate = fn
    return self

  def _SetWithoutNotify(self, obj, value):
    self._SetInstanceAttr(obj, value)

  def __set__(self, obj, value):
    self._SetWithoutNotify(obj, self.validate(obj, value))
    self.CallCallbacks(obj)

  def CallCallbacks(self, obj):
    for i in self.callbacklist:
      i(obj)


class Bool(Attr):
  """An attribute that is always either 0 or 1.

  You can set it to the strings 'true' or 'false' (case insensitive) or
  '0' or '1' or the numbers 0, 1, True, or False.
  """

  def validate(self, obj, value):
    if value is None:
      return value
    s = str(value).lower()
    if s in ('true', '1'):
      return True
    elif s in ('false', '0', '', None):
      return False
    else:
      try:
        return float(s) and True or False
      except ValueError:
        raise ValueError('%r is not a valid boolean' % (value,))


class _SignedBasicType(long):
  """A wrapper class for int that tells api_soap.Soapify() it's signed."""

  xsitype = 'xsd:int'

  def __new__(cls, *args, **kwargs):
    return long.__new__(cls, *args, **kwargs)


class _UnsignedBasicType(long):
  """A wrapper class for int that tells api_soap.Soapify() it's unsigned."""

  xsitype = 'xsd:unsignedInt'

  def __new__(cls, *args, **kwargs):
    return long.__new__(cls, *args, **kwargs)


class Int(Attr):
  """An attribute that is always an integer."""

  def validate(self, obj, value):
    return _SignedBasicType(value)


class Unsigned(Attr):
  """An attribute that is always an integer >= 0."""

  def validate(self, obj, value):
    v = _UnsignedBasicType(value)
    if v < 0:
      raise ValueError('%r must be >= 0' % value)
    return v


class Float(Attr):
  """An attribute that is always a floating point number."""

  def validate(self, obj, value):
    return float(value)


class String(Attr):
  """An attribute that is always a string (actually unicode) or None."""

  def _encode(self, value):
    """Find a suitable representation."""
    try:
      return unicode(value)
    except UnicodeDecodeError:
      print 'string is not unicode: %r' % value

    try:
      return unicode(value, 'utf-8', 'replace')
    except UnicodeDecodeError:
      pass

    return value.decode('iso-8859-1')

  def validate(self, obj, value):
    if value is None:
      return None
    return self._encode(value)


class Enum(Attr):
  """An attribute that is always one of the given values.

  The values are usually strings in TR-069, but this is not enforced.
  """

  def __init__(self, values, init=None):
    super(Enum, self).__init__(init=init)
    self.values = frozenset(values)

  def validate(self, obj, value):
    if value not in self.values:
      raise ValueError('%r invalid; value values are %r'
                       % (value, self.values))
    return value


class Date(Attr):
  """An attribute that is always a datetime.datetime object."""

  def validate(self, obj, value):
    # pylint: disable=g-explicit-bool-comparison
    if value is None or value == '':
      return None
    try:
      f = float(value)
    except ValueError:
      return cwmpdate.parse(value)
    else:
      return datetime.datetime.utcfromtimestamp(f)


class MacAddr(Attr):
  """An attribute that is always a MAC address or None."""

  def validate(self, obj, value):
    if not value:
      return None
    if not MACADDR_REGEX.match(str(value)):
      raise ValueError('%r is not a MAC address' % value)
    return value


class IP4Addr(Attr):
  """An attribute that is always an IPv4 address or None."""

  def validate(self, obj, value):
    if not value:
      return None
    try:
      socket.inet_pton(socket.AF_INET, str(value))
    except socket.error:
      raise ValueError('%r is not an IPv4 address' % value)
    return value


class IPv4AddrList(Attr):
  """Validates a comma-separated list of IPv4 addresses."""

  def validate(self, obj, value):
    if not value:
      return value
    addresses = str(value).split(',')
    for address in addresses:
      try:
        socket.inet_pton(socket.AF_INET, address)
      except socket.error:
        raise ValueError('%s is not an IPv4 address.' % address)
    return value


class IP6Addr(Attr):
  """An attribute that is always an IPv6 address or None."""

  def validate(self, obj, value):
    if not value:
      return None
    try:
      socket.inet_pton(socket.AF_INET6, str(value))
    except socket.error:
      raise ValueError('%r is not an IPv6 address' % value)
    return value


_FileBacked_Notifier = None


def SetFileBackedNotifier(notifier):
  global _FileBacked_Notifier
  _FileBacked_Notifier = notifier


class FileBacked(Attr):
  """An attribute that is actually a string stored in a file.

  If delete_if_empty is True and the string is set to empty or None,
  deletes the file.
  If the file doesn't exist, the value is the empty string.
  """

  def __init__(self, filename_ptr, attr, delete_if_empty=True,
               file_owner=None, file_group=None):
    super(FileBacked, self).__init__()
    self.notifier = None
    if isinstance(filename_ptr, basestring):
      # Handle it if someone just provides a filename directly instead
      # of a [filename]
      self.filename_ptr = [filename_ptr]
    else:
      # A one-element list containing a filename, so that the filename
      # itself can be reassigned later, eg. by a unit test
      self.filename_ptr = filename_ptr
    self.attr = attr
    self.validate = attr.validate
    self.delete_if_empty = delete_if_empty
    self.file_owner = file_owner
    self.file_group = file_group
    if hasattr(attr, 'SetWrapper'):
      attr.SetWrapper(self)

  def SetWrapper(self, wrapattr):
    super(FileBacked, self).SetWrapper(wrapattr)
    if hasattr(self.attr, 'SetWrapper'):
      self.attr.SetWrapper(self)

  def _GetData(self, obj):
    """Returns a tuple (val, filename, watch) corresponding to this object."""
    try:
      return self._GetInstanceAttr(obj)
    except AttributeError:
      return None, None, None

  def GetFileName(self, obj):
    _, filename, _ = self._GetData(obj)
    if not filename:
      return self.filename_ptr[0]
    return filename

  def SetFileName(self, obj, filename):
    val, _, _ = self._GetData(obj)
    self._SetInstanceAttr(obj, (val, filename, None))
    self._RegisterNotifier(obj)

  def _CallRefCallbacks(self, obj_ref):
    """CallCallbacks using a weakref, only if the weakref is still valid."""
    obj = obj_ref()
    if obj:
      self.CallCallbacks(obj)

  def _RegisterNotifier(self, obj):
    if not obj: return
    val, filename, watch = self._GetData(obj)
    if not watch and _FileBacked_Notifier:
      # This is a little tricky.  You might think we'd just register the
      # notifier in the FileBacked constructor, but that doesn't work for
      # several reasons:
      #  - Descriptor constructors are called at the time the containing
      #    class is *defined*, not when it is instantiated, which is very
      #    early, and only once per class, not per instance.
      #  - _FileBacked_Notifier has probably not been constructed yet at that
      #    time.
      #  - We don't want to inotify on a file just because there exists a
      #    class that contains a FileBacked that might need notifications,
      #    if that class were instantiated.
      #
      # So instead, we start watching the file only the first time someone
      # gets or sets the FileBacked object.  This actually makes sense: a
      # program that has never looked at the content presumably doesn't care
      # what it contains anyway, so it also doesn't care if the content
      # changes.  And it allows us to defer creating the notifier until
      # much later.
      #
      # We store the Watch object inside the object instance's own
      # dictionary, so that when the object goes away, the notifier gets
      # unregistered too.
      #
      # To make matters worse, since the Watch needs a callback, and the
      # callback is a reference to the object being called, that creates a
      # circular reference, which would prevent the object from being
      # cleaned up.  So we use a weakref instead when generating the callback.
      obj_ref = weakref.ref(obj)
      try:
        watch = _FileBacked_Notifier.WatchObj(
            self.GetFileName(obj),
            lambda: self._CallRefCallbacks(obj_ref))
      except _FileBacked_Notifier.Error as e:
        # Not fatal, but will retry registering next time
        print repr(e)
      else:
        self._SetInstanceAttr(obj, (val, filename, watch))

  def __get__(self, obj, _):
    if obj is None:
      return self
    self._RegisterNotifier(obj)
    try:
      content = open(self.GetFileName(obj)).read().rstrip()
    except IOError as e:
      # If file doesn't exist, then use None.  Unless overridden, validate()
      # will convert this to ''.
      if e.errno == errno.ENOENT:
        return self.validate(obj, None)
      raise
    try:
      v = self.validate(obj, content)
    except ValueError:
      v = ''
    try:
      old_v, filename, watch = self._GetInstanceAttr(obj)
    except AttributeError:
      old_v, filename, watch = '', None, None
    if v != old_v and (old_v, v) not in [(None, ''), ('', None)]:
      self._SetInstanceAttr(obj, (v, filename, watch))
      self.CallCallbacks(obj)
    return v

  # Note: don't pass this function any special parameters.  WaitUntilIdle
  # will schedule up to 1 call of this function with *each* combination
  # of parameters it is passed, which is probably not what you want.
  @mainloop.WaitUntilIdle
  def _ReallyWriteFile(self, obj):
    filename = self.GetFileName(obj)
    try:
      os.rename(filename + '.tmp', filename)
    except OSError as e:
      if e.errno == errno.ENOENT:
        helpers.Unlink(filename)
      else:
        raise

  def _WriteFile(self, obj, value):
    """Writes the data out the file. The file is updated at idle time."""

    # First write a .tmp file.  We do this to catch exceptions where the
    # directory doesn't exist or permission issues etc.  Once we write a
    # tmp file, _ReallyWriteFile will schedule to rename the tmp file to the
    # real file.  This can still fail if we don't have permission to the actual
    # file but we have permission to the directory, but that seems less likely
    # then the directory just not existing.
    #
    tmpname = self.GetFileName(obj) + '.tmp'
    if value in [None, '']:
      if self.delete_if_empty:
        helpers.Unlink(tmpname)
      else:
        helpers.WriteFileAtomic(tmpname, '',
                                owner=self.file_owner, group=self.file_group)
    else:
      data = unicode(value).rstrip().encode('utf-8') + '\n'
      helpers.WriteFileAtomic(tmpname, data,
                              owner=self.file_owner, group=self.file_group)
    self._ReallyWriteFile(obj)

  def _SetWithoutNotify(self, obj, value):
    self._RegisterNotifier(obj)
    _, filename, watch = self._GetData(obj)
    self._SetInstanceAttr(obj, (value, filename, watch))  # cache this value
    self._WriteFile(obj, value)


class _Proxy(Attr):
  """Base for classes that wrap a property. See Trigger and ReadOnly."""

  def __init__(self, attr):
    super(_Proxy, self).__init__()
    self.attr = attr
    if hasattr(attr, 'SetWrapper'):
      attr.SetWrapper(self)

  def __get__(self, obj, _):
    if obj is None:
      return self
    return self.attr.__get__(obj, None)

  def SetWrapper(self, wrapattr):
    super(_Proxy, self).SetWrapper(wrapattr)
    if hasattr(self.attr, 'SetWrapper'):
      self.attr.SetWrapper(wrapattr)

  def validate(self, obj, value):
    f = getattr(self.attr, 'validate', None)
    if f: return f(obj, value)
    return value

  def validator(self, valfunc):
    f = getattr(self.attr, 'validator', None)
    if f:
      f(valfunc)
    else:
      Attr.validator(self, valfunc)
    return self

  def _SetWithoutNotify(self, obj, value):
    f = getattr(self.attr, '_SetWithoutNotify', None)
    if f: return f(obj, value)
    return self.attr.__set__(obj, value)


class Trigger(_Proxy):
  """A type descriptor that calls obj.Triggered() whenever its value changes.

  The 'attr' parameter to __init__ must be a descriptor itself.  So it
  could be an object derived from Attr (above), or an @property.  Examples:

    class X(object):
      def __init__(self):
        self._thing = 7
      def Triggered(self):
        print 'woke up!'
      a = Trigger(Attr())
      b = Trigger(Bool())

      @property
      def thing(self):
        return self._thing

      @Trigger
      @thing.setter
      def thing(self, value):
        self._thing = value

    x = X()
    x.a = 'hello'  # triggers
    x.a = 'hello'  # unchanged: no trigger
    b = False      # default value was None, so triggers
    b = '0'        # still false; no trigger
    thing = 7      # same as original value; no trigger
    thing = None   # triggers
  """

  def __init__(self, attr):
    super(Trigger, self).__init__(attr=attr)
    self.__no_trigger = 0
    if hasattr(self.attr, 'callbacklist'):
      self.attr.callbacklist.append(self._Trigger)

  def _Trigger(self, obj):
    if not self.__no_trigger:
      obj.Triggered()

  def __set__(self, obj, value):
    # Prevent multi-triggers caused by setting the inner attribute, which
    # causes a callback on the inner object, which calls _Trigger.  Normally
    # that's what we want, but not now since we'll call Triggered() ourselves
    # if necessary.
    self.__no_trigger += 1
    try:
      old = self.__get__(obj, None)
      super(Trigger, self).__set__(obj, value)
      new = self.__get__(obj, None)
    finally:
      self.__no_trigger -= 1
    if old != new:
      # the attr's __set__ function might have rejected the change; only
      # call Triggered if it *really* changed.
      obj.Triggered()


def TriggerBool(*args, **kwargs):
  return Trigger(Bool(*args, **kwargs))


def TriggerInt(*args, **kwargs):
  return Trigger(Int(*args, **kwargs))


def TriggerUnsigned(*args, **kwargs):
  return Trigger(Unsigned(*args, **kwargs))


def TriggerFloat(*args, **kwargs):
  return Trigger(Float(*args, **kwargs))


def TriggerString(*args, **kwargs):
  return Trigger(String(*args, **kwargs))


def TriggerEnum(*args, **kwargs):
  return Trigger(Enum(*args, **kwargs))


def TriggerDate(*args, **kwargs):
  return Trigger(Date(*args, **kwargs))


def TriggerMacAddr(*args, **kwargs):
  return Trigger(MacAddr(*args, **kwargs))


def TriggerIP4Addr(*args, **kwargs):
  return Trigger(IP4Addr(*args, **kwargs))


def TriggerIPv4AddrList(*args, **kwargs):
  return Trigger(IPv4AddrList(*args, **kwargs))


def TriggerIP6Addr(*args, **kwargs):
  return Trigger(IP6Addr(*args, **kwargs))


class ReadOnly(_Proxy):
  """A type descriptor that prevents setting the wrapped Attr().

  Since usually *someone* needs to be able to set the value, we also add a
  Set() method that overrides the read-only-ness.  The syntax for doing it
  is a little weird, which is a good reminder that you're not supposed to
  change read-only objects.

  Example:
    class X(object):
      b = ReadOnly(Bool(True))

    x = X()
    print x.b          # True
    x.b = False        # raises AttributeError
    X.b.Set(x, False)  # actually sets the bool
  """

  @property
  def callbacklist(self):
    # Normally we just want to use the attr's callbacklist, so that changes
    # it makes internally will trigger callbacks.  But if we wrap a
    # basic property that doesn't have callbacks, we'll have to provide our
    # own callback list.
    return getattr(self.attr, 'callbacklist', self._callbacklist)

  def validate(self, unused_obj, _):
    # this is the same exception raised by a read-only @property
    raise AttributeError("can't set read-only attribute")

  def __set__(self, unused_obj, _):
    # this is the same exception raised by a read-only @property
    raise AttributeError("can't set read-only attribute")

  def Set(self, obj, value):
    """Override the read-only-ness; generally for internal use."""
    return self.attr.__set__(obj, value)


def ReadOnlyBool(*args, **kwargs):
  return ReadOnly(Bool(*args, **kwargs))


def ReadOnlyInt(*args, **kwargs):
  return ReadOnly(Int(*args, **kwargs))


def ReadOnlyUnsigned(*args, **kwargs):
  return ReadOnly(Unsigned(*args, **kwargs))


def ReadOnlyFloat(*args, **kwargs):
  return ReadOnly(Float(*args, **kwargs))


def ReadOnlyString(*args, **kwargs):
  return ReadOnly(String(*args, **kwargs))


def ReadOnlyEnum(*args, **kwargs):
  return ReadOnly(Enum(*args, **kwargs))


def ReadOnlyDate(*args, **kwargs):
  return ReadOnly(Date(*args, **kwargs))


def ReadOnlyMacAddr(*args, **kwargs):
  return ReadOnly(MacAddr(*args, **kwargs))


def ReadOnlyIP6Addr(*args, **kwargs):
  return ReadOnly(IP6Addr(*args, **kwargs))


def ReadOnlyIP4Addr(*args, **kwargs):
  return ReadOnly(IP4Addr(*args, **kwargs))


class NumberOf(ReadOnly):
  """An attribute which returns the length of some other object.

    CWMP frequently defines FooNumberOfEntries parameters, to return
    the number of Foo objects.
  """

  def __init__(self, listname):
    super(NumberOf, self).__init__(Unsigned())
    self.listname = listname

  def __get__(self, obj, _):
    if obj is None:
      return self
    try:
      return len(getattr(obj, self.listname))
    except TypeError as e:
      raise TypeError('%s: %s' % (self.listname, e))


def tryattr(obj, attrname, value):
  """Like setattr(), but validates the value without actually setting it.

  For attributes that exist but have no validator, acts as if the validator
  function allows all values.  Note: just because tryattr() returns success
  doesn't guarantee that setattr() would return success.  You need to still
  be able to handle exceptions in setattr() (due to race conditions, missing
  validators, or any other reason.)

  Args:
    obj: the object containing the attr.
    attrname: the name of the attribute to set.
    value: the value to try setting the attribute to.
  Returns:
    value, or a modified version of value as fixed up by the validator (eg.
      to coerce the data type).
  Raises:
    Any exception the validator might raise.
  """
  try:
    prop = getattr(type(obj), attrname)
  except AttributeError:
    if hasattr(obj, attrname):
      return value  # just a plain value, definitely writable
    else:
      raise  # nonexistent
  validator = getattr(prop, 'validate', None)
  if validator:
    return validator(obj, value)
  else:
    return value


def AddNotifier(cls, attrname, notifier):
  """Registers the notifier with the given attribute of the class.

  And adds the notifier to the attribute's callbacklist. Now, whenever
  __set__() is called on the attribute of the class, all the registered
  notifiers are notified and hence, all the callback functions in the list
  are called. We only add a notifier on a class (type) and not an instance
  of a class. This is because we want to add notifiers on all objects of a
  particular type (and not just a single object), so that all those notifiers
  are notified whenever the attribute value of that class is set.

  Args:
    cls: the class to instrument.
    attrname: The attribute to monitor.
    notifier: The notifier to call.
  Raises:
    TypeError: if cls is an object and not a class.
  """

  if not isinstance(cls, type):
    t = 'AddNotifier can only be registered on a class, not an instance'
    raise TypeError(t)
  prop = getattr(cls, attrname)
  prop.callbacklist.append(notifier)
