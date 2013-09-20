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
import pycurl
import select
import sys

# NOTE(apenwarr): libcurl 7.22 (at least) has a bug when used with epoll.
#  If an HTTP request causes a redirect, and we get the redirect response
#  very quickly (as we do in the tests in this file), libcurl will disconnect
#  the socket and then reconnect on the same fd, without telling tornado to
#  unregister and re-register its events.  With epoll, this is fatal and the
#  tests will fail.  The proper fix for this is to upgrade to libcurl 7.31
#  or later, but since not everyone will do that, let's disable epoll if we
#  find you have an old version of libcurl and are running this test.
#  This code has to come before any tornado imports, because tornado checks
#  for the existence of epoll when it is first imported
if pycurl.version.startswith('libcurl/') and pycurl.version < 'libcurl/7.31':
  sys.stderr.write('WARNING: old libcurl; epoll disabled. '
                   'Get libcurl 7.31 or newer.\n')
  if hasattr(select, 'epoll'):
    del select.epoll
