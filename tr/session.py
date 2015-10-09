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
# pylint: disable=invalid-name
#
"""Implement the TR-069 CWMP Sesion handling."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import collections
import Cookie
import functools
import types
import tornado.httpclient
import tornado.ioloop

# SPEC3 = TR-069_Amendment-3.pdf
# http://www.broadband-forum.org/technical/download/TR-069_Amendment-3.pdf

graphviz = r"""
digraph DLstates {
  node [shape=box]

  CONNECT [label="CONNECT"]
  ACTIVE [label="ACTIVE\nsend responses or requests"]
  ONHOLD [label="ONHOLD\nsend responses"]
  NOMORE [label="NOMORE\nsend responses"]
  DONE [label="DONE\nclose session"]

  CONNECT -> ACTIVE [label="Send Inform"]
  ACTIVE -> ONHOLD [label="onhold=True"]
  ONHOLD -> ACTIVE [label="onhold=False"]
  ACTIVE -> NOMORE [label="send empty POST"]
  NOMORE -> DONE [label="receive empty Body"]
}
"""

HTTPCLIENT = tornado.httpclient.AsyncHTTPClient
_run_at_end = []


class CwmpSession(object):
  """State machine to handle the lifecycle of a TCP session with the ACS."""

  CONNECT = 'CONNECT'
  ACTIVE = 'ACTIVE'
  ONHOLD = 'ONHOLD'
  NOMORE = 'NOMORE'
  DONE = 'DONE'

  def __init__(self, acs_url, ioloop=None):
    self.http = HTTPCLIENT(max_simultaneous_connections=1,
                           io_loop=ioloop or tornado.ioloop.IOLoop.instance())
    self.acs_url = acs_url
    self.cookies = None
    self.my_ip = None
    self.ping_received = False
    self.state = self.CONNECT
    self.cookies = Cookie.SimpleCookie()

  def state_update(self, sent_inform=None, on_hold=None,
                   cpe_to_acs_empty=None, acs_to_cpe_empty=None):
    if self.state == self.CONNECT:
      if sent_inform:
        self.state = self.ACTIVE
    elif self._active():
      if on_hold:
        self.state = self.ONHOLD
      elif cpe_to_acs_empty:
        self.state = self.NOMORE
    elif self._onhold():
      if on_hold is False:  # not just the default None; explicitly False
        self.state = self.ACTIVE
    elif self._nomore():
      if acs_to_cpe_empty:
        self.state = self.DONE

  def _connect(self):
    return self.state == self.CONNECT

  def _active(self):
    return self.state == self.ACTIVE

  def _onhold(self):
    return self.state == self.ONHOLD

  def _nomore(self):
    return self.state == self.NOMORE

  def _done(self):
    return self.state == self.DONE

  def inform_required(self):
    return True if self._connect() else False

  def request_allowed(self):
    return True if self._active() else False

  def response_allowed(self):
    return True if self._active() or self._onhold() or self._nomore() else False

  def should_close(self):
    return True if self._done() else False

  def __del__(self):
    self.close()

  def close(self):
    cache.flush()
    _RunEndCallbacks()
    self.http = None
    return self.ping_received


def _make_hashable(obj):
  if isinstance(obj, collections.Hashable):
    return obj
  else:
    return repr(obj)


class cache(object):
  """A global cache of arbitrary data for the lifetime of one CWMP session.

  @session.cache is a decorator to cache the return
  value of a function for the remainder of the session with the ACS.
  Calling the function again with the same arguments will be serviced
  from the cache.

  This is intended for very expensive operations, particularly where
  a process is forked and its output parsed.
  """

  _thecache = dict()

  @staticmethod
  def flush():
    """Flush all cached data."""
    if cache._thecache:
      print 'Flushing session cache (%d entries)' % len(cache._thecache)
    cache._thecache.clear()

  def __init__(self, func):
    self.func = func
    self.obj = None

  def __get__(self, obj, objtype):
    """Support instance methods."""
    self.obj = obj
    return functools.partial(self.__call__, obj)

  def __call__(self, *args, **kwargs):
    key = self._cache_key(args, kwargs)
    try:
      return cache._thecache[key]
    except KeyError:
      val = self.func(*args, **kwargs)
      if isinstance(val, types.GeneratorType):
        raise TypeError('cannot cache generators; use cache_as_list instead')
      cache._thecache[key] = val
      return val

  def _cache_key(self, args, kwargs):
    """Concatenate the function, object, and all arguments."""
    return (_make_hashable(self.func),
            _make_hashable(self.obj),
            tuple(_make_hashable(x) for x in list(args)),
            tuple(_make_hashable(x) for x in list(kwargs)))


def cache_as_list(f):
  """Like cache(), but caches the return value as a list.

  You can't cache the output of generator functions (ie. functions that
  use yield) because that doesn't make sense.  Rather than silently converting
  such output to a list, you can declare it using @tr.session.cache_as_list
  instead of @tr.session.cache, and explicitly do the conversion.

  Args:
    f: the function being wrapped.
  Returns:
    A new function that, when called, passes its arguments to f and typecasts
    its return value into a list.
  """
  @cache
  def AsList(*args, **kwargs):
    return list(f(*args, **kwargs))
  return AsList


def RunAtEnd(func):
  """Schedule a function to run as soon as this ACS session ends."""
  if func not in _run_at_end:
    _run_at_end.append(func)


def _RunEndCallbacks():
  """Call any callbacks registered by RunAtEnd()."""
  while _run_at_end:
    func = _run_at_end.pop(0)
    func()


def main():
  # pylint: disable=C6003
  print('# pipe this to grapviz, ex:')
  print('# ./session.py | dot -Tpdf -osession.pdf')
  print(graphviz)


if __name__ == '__main__':
  main()
