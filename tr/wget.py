#!/usr/bin/python
# Copyright 2011 Google Inc. All Rights Reserved.
#
# TR-069 has mandatory attribute names that don't comply with policy
#pylint: disable-msg=C6409
#pylint: disable-msg=W0404
#
"""A class wrapping wget, to download files."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import os
import subprocess
import tornado.httpclient
import tornado.ioloop


class Wget(object):
  """Fetch a file via a wget subprocess. Interface vaguely resembles tornado.httpclient."""

  def __init__(self, io_loop=None):
    self.ioloop = io_loop or tornado.ioloop.IOLoop.instance()
    self.subproc = None
    self.callback = None
    self.request = None
    self.wgetname = 'wget'  # unit tests can override

  def _WgetExitToHttpCode(self, exitcode):
    """Maps wget exit codes to HTTP errors. -1 means "other error" """
    mapping = { 8 : 404,  # server error. We assume 404 Not Found.
                6 : 401,  # Unauthorized
                0 : 200 }
    return mapping.get(exitcode, -1)

  def _EndProc(self):
    """Get the exit code of the wget, and call the callback."""
    rc = 1
    if self.subproc:
      self.ioloop.remove_handler(self.subproc.stdout.fileno())
      if self.subproc.poll() is None:
        self.subproc.kill()
      rc = self.subproc.poll()
      self.subproc = None
    if self.callback:
      resp = tornado.httpclient.HTTPResponse(self.request, self._WgetExitToHttpCode(rc))
      self.callback(resp)

  def fetch(self, req, callback, outfile=None):
    """Fetch a file, store it in outfile.

    Args:
      req - a tornado.httpclient.HTTPRequest describing the desired file.
      callback - will be called when the fetch is complete.
      outfile - string filename of the desired destination.
    """
    self._EndProc()
    self.request = req
    self.callback = callback
    args = [self.wgetname, '--quiet']
    if req.auth_username is not None and req.auth_password is not None:
      args.append('--user=' + req.auth_username)
      args.append('--password=' + req.auth_password)
    if outfile is not None:
      args.append('--output-document=' + outfile)
    args.append(req.url)
    self.subproc = subprocess.Popen(args, stdout=subprocess.PIPE)
    self.ioloop.add_handler(self.subproc.stdout.fileno(),
                            self._GotData, self.ioloop.READ)

  #pylint: disable-msg=W0613
  def _GotData(self, fd, events):
    data = os.read(fd, 4096)
    if not data:
      self._EndProc()


def testcallback():
  print "Download done!"

if __name__ == '__main__':
  ioloop = tornado.ioloop.IOLoop.instance()
  wget = Wget(ioloop)
  req = tornado.httpclient.HTTPRequest(url="http://codingrelic.geekhold.com")
  wget.fetch(req, testcallback, "/tmp/wget_fetch_test.html")
  ioloop.start()
