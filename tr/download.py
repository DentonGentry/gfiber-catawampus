#!/usr/bin/python
# Copyright 2011 Google Inc. All Rights Reserved.
#
"""Handlers for tr-69 Download and Scheduled Download"""

__author__ = 'dgentry@google.com (Denton Gentry)'

import glob
import json
import os
import sys
import tempfile
import time
import tornado
import tornado.httpclient
import tornado.ioloop
import tornado.web

# Directory where Download states will be written to the filesystem.
STATE_DIR = "/tmp"

# Used as both the XML tag for download objects, and a prefix for filenames.
ROOTNAME = "tr69_dnld"

# Unit tests can override these to pass in mocks
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


class HttpDownload(object):
  # States a download passes through:
  DELAYING = "DELAYING"
  DOWNLOADING = "DOWNLOADING"
  INSTALLING = "INSTALLING"
  REBOOTING = "REBOOTING"
  CONCLUDING = "CONCLUDING"

  def __init__(self, ioloop):
    self.ioloop = ioloop

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
    self.stateobj = PersistentObject(rootname=ROOTNAME, **kwargs)
    # I dislike when APIs require NTP-related bugs in my code.
    self.ioloop.add_timeout(time.time() + delay_seconds, self.delay)

    # tr-69 DownloadResponse: 1 = Download has not yet been completed
    # and applied
    return 1

  def delay(self):
    self.tempfile = tempfile.NamedTemporaryFile(delete=False)
    req = tornado.httpclient.HTTPRequest(
        url = self.stateobj.url,
        auth_username = self.stateobj.username,
        auth_password = self.stateobj.password,
        request_timeout = 3600.0,
        streaming_callback = self.tempfile.write,
        allow_ipv6 = True)
    self.http_client = DOWNLOADER()
    self.http_client.fetch(req, self.async_callback)
    self.stateobj.Update(download_start_time=time.time())

  def async_callback(self, response):
    self.stateobj.Update(download_end_time=time.time())
    self.tempfile.flush()
    self.tempfile.close()
    if response.error:
      print "Failed"
      os.unlink(self.tempfile.name)
      self.ioloop.stop()
    else:
      print("Success: %s" % self.tempfile.name)
      self.ioloop.stop()


def main():
  ioloop = tornado.ioloop.IOLoop.instance()
  dl = HttpDownload(ioloop)
  if len(sys.argv) > 1:
    url = sys.argv[1]
  else:
    url = "http://codingrelic.geekhold.com/"
  print 'using URL: %s' % url
  dl.download(url=url, delay_seconds=0)
  ioloop.start()

if __name__ == '__main__':
  main()
