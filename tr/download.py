#!/usr/bin/python
# Copyright 2011 Google Inc. All Rights Reserved.
#
"""Handlers for tr-69 Download and Scheduled Download"""

__author__ = 'dgentry@google.com (Denton Gentry)'

import glob
import hashlib
import json
import os
import random
import sys
import tempfile
import time
import tornadi_fix
import tornado
import tornado.httpclient
import tornado.ioloop
import tornado.web

# Directory where Download states will be written to the filesystem.
STATE_DIR = "/tmp"

# Used as both the XML tag for download objects, and a prefix for filenames.
ROOTNAME = "tr69_dnld"

# Unit tests can override this to pass in a mock
DOWNLOADER = tornado.httpclient.AsyncHTTPClient


class PersistentObject(object):
  """Object holding simple data fields which can persist itself to json."""

  def __init__(self, rootname="object", filename=None, **kwargs):
    """Create either a fresh new object, or restored state from filesystem.

    Args:
      rootname: the tag for the root of the json file for this object.
      filename: name of an json file on disk, to restore object state from.
        If filename is None then this is a new object, and will create
        a file for itself in STATE_DIR.
      kwargs: Parameters to be passed to self.Update
    """
    self.rootname = rootname
    self._fields = {}
    if filename:
      self._ReadFromFS(filename)
    else:
      prefix = rootname + "_"
      f = tempfile.NamedTemporaryFile(
          mode="a+", prefix=prefix, dir=STATE_DIR, delete=False)
      filename = f.name
      f.close()
    self.filename = filename
    if kwargs:
      self.Update(**kwargs)

  def __getattr__(self, name):
    return self.__getitem__(name)

  def __getitem__(self, name):
    return self._fields[str(name)]

  def __str__(self):
    return self._ToJson()

  def __unicode__(self):
    return self.__str__()

  def Update(self, **kwargs):
    """Atomically update one or more parameters of the object.

    One might reasonably ask why this is an explicit call and not just
    setting parameters like self.foo="Bar". The motivation is atomicity.
    We want the state saved to the filesystem to be consistent, and not
    write out a partially updated object each time a parameter is changed.

    When this call returns, the state has been safely written to the
    filesystem. Any errors are reported by raising an exception.

    Args:
      **kwargs: Parameters to be updated.
    """
    self._fields.update(kwargs)
    self._WriteToFS()

  def Get(self, name):
    return self._fields.get(name, None)

  def values(self):
    return self._fields.values()

  def items(self):
    return self._fields.items()

  def _ToJson(self):
    return json.dumps(self._fields, indent=2)

  def _FromJson(self, string):
    d = json.loads(str(string))
    assert isinstance(d, dict)
    return d

  def _ReadFromFS(self, filename):
    """Read a json file back to an PersistentState object."""
    d = self._FromJson(open(filename).read())
    self._fields.update(d)

  def _WriteToFS(self):
    """Write PersistentState object out to an json file."""
    f = tempfile.NamedTemporaryFile(
        mode="a+", prefix="tmpwrite", dir=STATE_DIR, delete=False)
    f.write(self._ToJson())
    f.close()
    os.rename(f.name, self.filename)


def GetDownloadObjects(rootname=ROOTNAME):
  globstr = STATE_DIR + "/" + rootname + "*"
  dnlds = []
  for f in glob.glob(globstr):
    dnlds.append(PersistentObject(rootname, f))
  return dnlds


class Installer(object):
  """Install a downloaded image and reboot.

  This default implementation returns an error response. Platforms are
  expected to implement their own Install object, and set
  tr.download.INSTALLER = their object.
  """
  def __init__(self, filename):
    self.filename = filename

  def install(self, callback):
    return (9002, 'No installer for this platform.')

  def reboot(self):
    return False

# Class to be called after image is downloaded. Platform code is expected
# to put its own installer here, the default returns failed to install.
INSTALLER = Installer


def _uri_path(url):
  pos = url.find('://')
  if pos >= 0:
    url = url[pos+3:]
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
  # States a download passes through:
  DELAYING = "DELAYING"
  DOWNLOADING = "DOWNLOADING"
  INSTALLING = "INSTALLING"
  REBOOTING = "REBOOTING"
  CONCLUDING = "CONCLUDING"

  def __init__(self, ioloop=None):
    self.ioloop = ioloop or tornado.ioloop.IOLoop.instance()

  def download(self, command_key=None, file_type=None, url=None,
               username=None, password=None, file_size=0,
               target_filename=None, delay_seconds=0):
    kwargs = dict(command_key=command_key,
                  file_type=file_type,
                  url=url,
                  username=username,
                  password=password,
                  file_size=file_size,
                  target_filename=target_filename,
                  delay_seconds=delay_seconds)
    self.auth_header = None
    self.tempfile = None
    self.stateobj = PersistentObject(rootname=ROOTNAME, **kwargs)
    # I dislike when APIs require NTP-related bugs in my code.
    self.ioloop.add_timeout(time.time() + delay_seconds, self.start_download)

    # tr-69 DownloadResponse: 1 = Download has not yet been completed
    # and applied
    return 1

  def start_download(self):
    print 'starting (auth_header=%r)' % self.auth_header
    if not self.tempfile:
      self.tempfile = tempfile.NamedTemporaryFile(delete=False)
    kwargs = dict(url=self.stateobj.url,
                  request_timeout=3600.0,
                  streaming_callback=self.tempfile.write,
                  allow_ipv6=True)
    if self.auth_header:
      kwargs.update(dict(headers=dict(Authorization=self.auth_header)))
    elif self.stateobj.username and self.stateobj.password:
      kwargs.update(dict(auth_username=self.stateobj.username,
                         auth_password=self.stateobj.password))
    req = tornado.httpclient.HTTPRequest(**kwargs)
    self.http_client = DOWNLOADER(io_loop=self.ioloop)
    self.http_client.fetch(req, self.async_callback)
    self.stateobj.Update(download_start_time=time.time())

  def calculate_auth_header(self, response):
    """HTTP Digest Authentication."""
    h = response.headers.get('www-authenticate', None)
    if not h:
      return
    authtype, paramstr = h.split(' ', 1)
    if authtype != 'Digest':
      return

    params = {}
    for param in paramstr.split(','):
      name, value = param.split('=')
      assert(value.startswith('"') and value.endswith('"'))
      params[name] = value[1:-1]

    uripath = _uri_path(self.stateobj.url)
    nc = '00000001'
    nonce = params['nonce']
    realm = params['realm']
    opaque = params.get('opaque', None)
    cnonce = str(random.getrandbits(32))
    username = self.stateobj.username
    password = self.stateobj.password
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

    returnlist = [('%s="%s"' % (k,v)) for k,v in returns.items()]
    return 'Digest %s' % ','.join(returnlist)

  def async_callback(self, response):
    """Called for each chunk of data downloaded."""
    if (response.error and response.error.code == 401 and
        not self.auth_header and
        self.stateobj.username and self.stateobj.password):
      print '401 error, attempting Digest auth'
      self.auth_header = self.calculate_auth_header(response)
      if self.auth_header:
        self.start_download()
        return

    if response.error:
      print "Failed: %r" % response.error
      print json.dumps(response.headers, indent=2)
      os.unlink(self.tempfile.name)
    else:
      self.done()
      print("Success: %s" % self.tempfile.name)

  def done(self):
    self.stateobj.Update(download_end_time=time.time())
    self.tempfile.flush()
    self.tempfile.close()
    self.install(self.tempfile.name)

  def install(self, filename):
    installer = INSTALLER(filename)
    (code, string) = installer.install(None)
    if code:
      # TODO(dgentry) send TransferComplete with failure code.
      pass
    else:
      installer.reboot()


def main():
  ioloop = tornado.ioloop.IOLoop.instance()
  dl = HttpDownload(ioloop)
  url = len(sys.argv) > 1 and sys.argv[1] or "http://www.google.com/"
  username = len(sys.argv) > 2 and sys.argv[2]
  password = len(sys.argv) > 3 and sys.argv[3]
  print 'using URL: %s' % url
  dl.download(url=url, username=username, password=password, delay_seconds=0)
  ioloop.start()

if __name__ == '__main__':
  main()
