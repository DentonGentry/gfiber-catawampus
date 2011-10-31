#!/usr/bin/python
# Copyright 2011 Google Inc. All Rights Reserved.
#
"""Handlers for tr-69 Download and Scheduled Download"""

__author__ = 'dgentry@google.com (Denton Gentry)'

import os
import tempfile
import time
import tornado
import tornado.httpclient
import tornado.ioloop
import tornado.web
import xml.etree.ElementTree as etree

# Directory where Download states will be written to the filesystem.
statedir = "/tmp"

class PersistentObject(object):
  """Object holding simple data fields which can presist itself to XML."""

  def __init__(self, rootname="object", filename=None, **kwargs):
    """Create either a fresh new object, or restored state from filesystem.

    Args:
      rootname: the tag for the root of the XML file for this object.
      filename: name of an XML file on disk, to restore object state from.
        If filename is None then this is a new object, and will create
        a file for itself in statedir.
      kwargs: Parameters to be passed to self.Update
    """
    self.rootname = rootname
    self._fields = {}
    if filename is not None:
      self._ReadFromFS(filename)
    else:
      f = tempfile.NamedTemporaryFile(
          mode="a+", prefix=rootname, dir=statedir, delete=False)
      filename = f.name
      f.close()
    self.filename = filename
    if len(kwargs) > 0:
      self.Update(**kwargs)

  def __getattr__(self, name):
    return self._fields[str(name)]

  def __getitem__(self, name):
    return self._fields[name]

  def __str__(self):
    return etree.tostring(self._ToXml())

  def __unicode__(self):
    return etree.tostring(self._ToXml())

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
    for key in kwargs:
      self._fields[key] = str(kwargs[key])
    self._WriteToFS()

  def _ReadFromFS(self, filename):
    root = etree.parse(filename).getroot()
    for field in root:
      self._fields[field.tag] = field.text

  def _ToXml(self):
    root = etree.Element(self.rootname)
    for key in self._fields:
      sub = etree.SubElement(root, key)
      sub.text = self._fields[key]
    return root

  def _WriteToFS(self):
    root = self._ToXml()
    tree = etree.ElementTree(root)
    f = tempfile.NamedTemporaryFile(
        mode="a+", prefix="tmpwrite", dir=statedir, delete=False)
    tree.write(f)
    f.close()
    os.rename(f.name, self.filename)

class HttpDownload(object):
  def download(self, ioloop, command_key=None, file_type=None, url=None,
               username=None, password=None, file_size=0, target_filename=None,
               delay_seconds=0):
    self.ioloop = ioloop
    self.command_key = command_key
    self.file_type = file_type
    self.url = url
    self.username = username
    self.password = password
    self.file_size = file_size
    self.target_filename = target_filename
    self.download_start_time = None
    self.download_complete_time = None

    self.tempfile = tempfile.NamedTemporaryFile(delete=False)

    # I dislike when APIs require NTP-related bugs in my code.
    ioloop.add_timeout(time.time() + delay_seconds, self.delay)

    # tr-69 DownloadResponse: 1 = Download has not yet been completed
    # and applied
    return 1

  def delay(self):
    req = tornado.httpclient.HTTPRequest(
        url = self.url,
        auth_username = self.username,
        auth_password = self.password,
        request_timeout = 3600.0,
        streaming_callback = self.streaming_callback,
        allow_ipv6 = True)
    http_client = tornado.httpclient.AsyncHTTPClient()
    http_client.fetch(req, self.async_callback)
    self.download_start_time = time.time()

  def streaming_callback(self, data):
    self.tempfile.write(data)

  def async_callback(self, response):
    self.tempfile.flush()
    self.tempfile.close()
    if response.error:
      print "Failed"
      os.unlink(self.tempfile.name)
    else:
      print("Success: %s" % self.tempfile.name)
      self.ioloop.stop()


def main():
  ioloop = tornado.ioloop.IOLoop.instance()
  dl = HttpDownload(ioloop,
                    url="http://codingrelic.geekhold.com/",
                    delay_seconds=0)
  ioloop.start()

if __name__ == '__main__':
  main()
