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
#
# pylint:disable=invalid-name
# pylint:disable=unused-argument

"""Handlers for tr-69 Download and Scheduled Download."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import hashlib
import json
import os
import random
import sys
import tempfile
import google3
import tornado
import tornado.httpclient
import tornado.ioloop
import tornado.web

# Unit tests can override this to pass in a mock
HTTPCLIENT = tornado.httpclient.AsyncHTTPClient
PERCENT_COMPLETE_FILE = '/tmp/cwmp/download_percent'
TEMPFILE = tempfile.NamedTemporaryFile

# tr-69 fault codes
DOWNLOAD_FAILED = 9010


def _uri_path(url):
  pos = url.find('://')
  if pos >= 0:
    url = url[pos + 3:]
  pos = url.find('/')
  if pos >= 0:
    url = url[pos:]
  return url


def calc_http_digest(method, uripath, qop, nonce, cnonce, nc,
                     username, realm, password):
  def H(s):
    return hashlib.md5(s).hexdigest()

  def KD(secret, data):
    return H(secret + ':' + data)
  A1 = username + ':' + realm + ':' + password
  A2 = method + ':' + uripath
  digest = KD(H(A1), nonce + ':' + nc + ':' + cnonce + ':' + qop + ':' + H(A2))
  return digest


class HttpDownload(object):
  """Holds the state for an in-progress download over HTTP."""

  def __init__(self, url, username=None, password=None,
               download_complete_cb=None, ioloop=None, download_dir=None):
    self.url = url
    self.username = username
    self.password = password
    self.download_complete_cb = download_complete_cb
    self.ioloop = ioloop or tornado.ioloop.IOLoop.instance()
    self.download_dir = download_dir

  def fetch(self):
    """Begin downloading file."""
    self.auth_header = None
    self.tempfile = None
    return self._start_download()

  def _start_download(self):
    """Starts downloading the given object."""
    print 'download: starting (auth_header=%r)' % self.auth_header
    self.content_length = 0
    self.downloaded_bytes = 0
    self.file_percent_complete = 0
    self.logged_percent_complete = 0
    self.headers = dict()
    if not self.tempfile:
      self.tempfile = TEMPFILE(delete=True, dir=self.download_dir)
    self.tempfile.truncate(0)
    self.tempfile.seek(0)
    kwargs = dict(url=self.url,
                  request_timeout=3600.0,
                  header_callback=self.header_callback,
                  streaming_callback=self.streaming_callback,
                  use_gzip=True, allow_ipv6=True,
                  user_agent='catawampus-tr69')
    if self.auth_header:
      kwargs.update(dict(headers=dict(Authorization=self.auth_header)))
    elif self.username and self.password:
      kwargs.update(dict(auth_username=self.username,
                         auth_password=self.password))
    req = tornado.httpclient.HTTPRequest(**kwargs)
    self.http_client = HTTPCLIENT(io_loop=self.ioloop)
    self.http_client.fetch(req, self._async_fetch_callback)

  def _IntOrZero(self, v):
    try:
      return int(v)
    except ValueError:
      return 0

  def header_callback(self, header):
    if ':' in header:
      (k, v) = header.split(':', 1)
      self.headers[k.strip()] = v.strip()
      if k.lower().startswith('content-length'):
        self.content_length = self._IntOrZero(v)

  def _output_dl_percentage(self, percent_complete):
    if percent_complete != self.file_percent_complete:
      self.file_percent_complete = percent_complete
      if PERCENT_COMPLETE_FILE:
        try:
          with open(PERCENT_COMPLETE_FILE, 'w+') as f:
            f.write(str(percent_complete))
        except IOError:
          print 'download: ERROR unable to write ' + PERCENT_COMPLETE_FILE
    if abs(percent_complete - self.logged_percent_complete) >= 10:
      self.logged_percent_complete = percent_complete
      print 'download: %d percent complete' % percent_complete

  def streaming_callback(self, buf):
    self.tempfile.write(buf)
    self.downloaded_bytes += len(buf)
    if self.content_length:
      percent_complete = (self.downloaded_bytes * 100) / self.content_length
      self._output_dl_percentage(percent_complete)

  def _calculate_auth_header(self, response):
    """HTTP Digest Authentication."""
    response.headers.update(self.headers)
    h = response.headers.get('www-authenticate', None)
    if not h:
      return
    authtype, paramstr = h.split(' ', 1)
    if authtype != 'Digest':
      return

    params = {}
    for param in paramstr.split(','):
      name, value = param.split('=')
      if value.startswith('"') and value.endswith('"'):
        value = value[1:-1]
      params[name.strip()] = value

    uripath = _uri_path(self.url)
    nc = '00000001'
    nonce = params['nonce']
    realm = params['realm']
    opaque = params.get('opaque', None)
    cnonce = str(random.getrandbits(32))
    username = self.username
    password = self.password
    qop = 'auth'
    returns = dict(uri=uripath,
                   qop=qop,
                   nc=nc,
                   cnonce=cnonce,
                   nonce=nonce,
                   username=username,
                   realm=realm)
    if opaque:
      returns['opaque'] = opaque
    returns['response'] = calc_http_digest(method='GET',
                                           uripath=uripath,
                                           qop=qop,
                                           nonce=nonce,
                                           cnonce=cnonce,
                                           nc=nc,
                                           username=username,
                                           realm=realm,
                                           password=password)

    returnlist = [('%s="%s"' % (k, v)) for k, v in returns.items()]
    return 'Digest %s' % ','.join(returnlist)

  def _async_fetch_callback(self, response):
    """Called at the end of the transfer."""
    if (response.error and response.error.code == 401 and
        not self.auth_header and self.username and self.password):
      print 'download: 401 fetching %s, attempting Digest auth' % self.url
      print json.dumps(response.headers, indent=2)
      self.auth_header = self._calculate_auth_header(response)
      if self.auth_header:
        self._start_download()
        print 'starting download again'
        return

    error_message = ''
    try:
      self.tempfile.flush()
    except IOError as e:
      error_message = 'download: ERROR flush failed %s' % str(e)

    if response.error:
      error_message = 'download: ERROR failed {0!r}'.format(response.error)
      print json.dumps(response.headers, indent=2)

    if error_message:
      try:
        # We got here because of an error, possibly ENOSPC due to the
        # filesystem being completely full. tempfile objects start
        # to run into pathological failures when the filesystem is
        # completely full, like failing to close() because fsync fails.
        # The following sequence has been empirically tested, to make
        # sure it deletes the file and releases the space.
        os.unlink(self.tempfile.name)
        self.tempfile = None
      except (IOError, OSError):
        print 'download: ERROR cannot clean up failed download.'
        pass
      self.download_complete_cb(DOWNLOAD_FAILED, error_message, None)
    else:
      self.download_complete_cb(0, '', self.tempfile)
      print('download: success {0}'.format(self.tempfile.name))


def main_dl_complete(ioloop, _, msg, filename):
  print msg
  ioloop = ioloop or tornado.ioloop.IOLoop.instance()
  ioloop.stop()


def main_dl_start(url, username, password, ioloop=None):
  tornado.httpclient.AsyncHTTPClient.configure(
      'tornado.curl_httpclient.CurlAsyncHTTPClient')
  import functools
  ioloop = ioloop or tornado.ioloop.IOLoop.instance()
  cb = functools.partial(main_dl_complete, ioloop)
  print 'using URL: %s username: %s password: %s' % (url, username, password)
  dl = HttpDownload(url=url, username=username, password=password,
                    download_complete_cb=cb, ioloop=ioloop)
  dl.fetch()
  ioloop.start()


def main():
  url = len(sys.argv) > 1 and sys.argv[1] or 'http://www.google.com/'
  username = password = None
  if len(sys.argv) > 3:
    username = sys.argv[2]
    password = sys.argv[3]
  main_dl_start(url, username, password)

if __name__ == '__main__':
  main()
