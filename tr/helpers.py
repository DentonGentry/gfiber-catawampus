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

"""Simple helper functions that don't belong elsewhere."""

__author__ = 'apenwarr@google.com (Avery Pennarun)'

import errno
import grp
import os
import pwd
import socket


# Unit tests can override these
CHOWN = os.chown
GETGID = grp.getgrnam
GETUID = pwd.getpwnam


def Unlink(filename):
  """Like os.unlink, but doesn't raise exception if file was missing already.

  After all, you want the file gone.  Its gone.  Stop complaining.

  Args:
    filename: the filename to delete
  Raises:
    OSError: if os.unlink() fails with other than ENOENT.
  """
  try:
    os.unlink(filename)
  except OSError, e:
    if e.errno != errno.ENOENT:
      raise


def _SetOwner(filename, owner, group):
  """Set the user and group for filename.

  Args:
    filename: the path to the file to change ownership of
    owner: the string name of the owning user, like 'daemon'
    group: the string name of the owning group, like 'wheel'

    None or the empty string means not to change the ownership.
  """
  uid = gid = -1
  if owner:
    uid = GETUID(owner).pw_uid
  if group:
    gid = GETGID(group).gr_gid
  CHOWN(filename, uid, gid)


class AtomicFile(object):
  """Like a normal file object, but atomically replaces file on close().

  Example:
      with AtomicFile('filename') as f:
        f.write('hello world')
        f.write('more stuff')

  The above program creates filename.tmp, writes content to it, then
  closes it and renames it to filename, thus overwriting any existing file
  named 'filename' atomically.
  """

  def __init__(self, filename, owner=None, group=None):
    self.filename = filename
    self.file = None
    self.owner = owner
    self.group = group

  def __enter__(self):
    filename = self.filename + '.tmp'
    self.file = open(filename, 'w')
    _SetOwner(filename, self.owner, self.group)
    return self.file

  def __exit__(self, unused_type, unused_value, unused_traceback):
    if self.file:
      self.file.close()
      os.rename(self.filename + '.tmp', self.filename)


def WriteFileAtomic(filename, data, owner=None, group=None):
  """A shortcut for calling AtomicFile with a static string as content."""
  with AtomicFile(filename, owner=owner, group=group) as f:
    f.write(data)


def IsIP4Addr(addr):
  """Returns True for valid dotted-quad IPv4 addresses like 1.2.3.4."""
  try:
    socket.inet_pton(socket.AF_INET, str(addr))
  except socket.error:
    return False
  return True


def IsIP6Addr(addr):
  """Returns true for valid IPv6 addresses."""
  try:
    socket.inet_pton(socket.AF_INET6, str(addr))
  except socket.error:
    return False
  return True
