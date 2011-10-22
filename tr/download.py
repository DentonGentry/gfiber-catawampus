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

    # tr-69 DownloadResponse: 1 = Download has not yet been completed and applied
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
