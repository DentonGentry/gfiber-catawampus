#!/usr/bin/python
# Copyright 2011 Google Inc. All Rights Reserved.
#
"""Handlers for tr-69 Download and Scheduled Download"""

__author__ = 'dgentry@google.com (Denton Gentry)'

import glob
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
      prefix = rootname + "_"
      f = tempfile.NamedTemporaryFile(
          mode="a+", prefix=prefix, dir=statedir, delete=False)
      filename = f.name
      f.close()
    self.filename = filename
    if len(kwargs) > 0:
      self.Update(**kwargs)

  def __getattr__(self, name):
    return self._fields[str(name)]

  def __getitem__(self, name):
    return self._fields[str(name)]

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
      self._fields[key] = kwargs[key]
    self._WriteToFS()

  def Get(self, name):
    if name in self._fields:
      return self._fields[name]
    return None

  def _is_integer(self, data):
    try:
      int(data)
      return True
    except ValueError:
      return False

  def _XMLType(self, data):
    if data is None:
      return "none"
    if self._is_integer(data):
      return "int"
    return "string"

  def _ReadFromFS(self, filename):
    """Read an XML file back to an PersistentState object."""
    root = etree.parse(filename).getroot()
    for field in root:
      fieldtype = field.attrib["type"]
      if fieldtype == "none":
        self._fields[field.tag] = None
      elif fieldtype == "int":
        self._fields[field.tag] = int(field.text)
      else:
        self._fields[field.tag] = str(field.text)

  def _ToXml(self):
    """Generate an ElementTree based on the current PersistentObject."""
    root = etree.Element(self.rootname)
    for key in self._fields:
      sub = etree.SubElement(root, key)
      data = self._fields[key]
      sub.text = str(data)
      sub.set("type", self._XMLType(data))
    return root

  def _WriteToFS(self):
    """Write PersistentState object out to an XML file."""
    root = self._ToXml()
    tree = etree.ElementTree(root)
    f = tempfile.NamedTemporaryFile(
        mode="a+", prefix="tmpwrite", dir=statedir, delete=False)
    tree.write(f)
    f.close()
    os.rename(f.name, self.filename)


# Used as both the XML tag for download objects, and a prefix for filenames.
dnld_rootname = "tr69_dnld"

def GetDownloadObjects(rootname=dnld_rootname):
  globstr = statedir + "/" + rootname + "*"
  dnlds = []
  for f in glob.glob(globstr):
    dnlds.append(PersistentObject(rootname, f))
  return dnlds


# Unit tests can override these to pass in mocks
dnld_client = tornado.httpclient.AsyncHTTPClient

class HttpDownload(object):
  # States a download passes through:
  DELAYING = "DELAYING"
  DOWNLOADING = "DOWNLOADING"
  INSTALLING = "INSTALLING"
  REBOOTING = "REBOOTING"
  CONCLUDING = "CONCLUDING"

  def download(self, ioloop, command_key=None, file_type=None, url=None,
               username=None, password=None, file_size=0, target_filename=None,
               delay_seconds=0):
    self.ioloop = ioloop
    kwargs = {"command_key" : command_key,
              "file_type" : file_type,
              "url" : url,
              "username" : username,
              "password" : password,
              "file_size" : file_size,
              "target_filename" : target_filename,
              "delay_seconds" : delay_seconds}
    self.stateobj = PersistentObject(rootname=dnld_rootname, **kwargs)
    # I dislike when APIs require NTP-related bugs in my code.
    self.ioloop.add_timeout(time.time() + delay_seconds, self.delay)

    # tr-69 DownloadResponse: 1 = Download has not yet been completed
    # and applied
    return 1

  def delay(self):
    req = tornado.httpclient.HTTPRequest(
        url = self.stateobj.url,
        auth_username = self.stateobj.username,
        auth_password = self.stateobj.password,
        request_timeout = 3600.0,
        streaming_callback = self.streaming_callback,
        allow_ipv6 = True)
    self.tempfile = tempfile.NamedTemporaryFile(delete=False)
    self.http_client = dnld_client()
    self.http_client.fetch(req, self.async_callback)
    self.stateobj.Update(download_start_time=time.time())

  def streaming_callback(self, data):
    self.tempfile.write(data)

  def async_callback(self, response):
    self.stateobj.Update(download_end_time=time.time())
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
  dl = HttpDownload()
  dl.download(ioloop, url="http://codingrelic.geekhold.com/", delay_seconds=0)
  ioloop.start()

if __name__ == '__main__':
  main()
