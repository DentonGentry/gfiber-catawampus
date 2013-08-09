#!/usr/bin/python
#
"""Implementation of the read-only Diagnostics UI."""

__author__ = 'anandkhare@google.com (Anand Khare)'

import hashlib
import google3
import tr.pyinotify
import tornado.ioloop
import tornado.web


# TODO(anandkhare): conditionally redirect only when needed
class MainHandler(tornado.web.RequestHandler):
  """If RG's connectivity to cloud is healthy, redirect to fiber.google.com."""

  def get(self):    # pylint: disable=g-bad-name
    self.redirect('https://fiber.google.com')


class DiagnosticsHandler(tornado.web.RequestHandler):
  """If no connectivity, display local diagnostics UI."""

  def get(self):    # pylint: disable=g-bad-name
    self.render('template.html')


class JsonHandler(tornado.web.RequestHandler):
  """Provides JSON-formatted content to be displayed in the UI."""

  def initialize(self):    # pylint: disable=g-bad-name
    self.oldchecksum = self.get_argument('checksum')

  @tornado.web.asynchronous
  def get(self):    # pylint: disable=g-bad-name
    if self.oldchecksum != self.application.newchecksum:
      try:
        self.set_header('Content-Type', 'text/javascript')
        self.write(tornado.escape.json_encode(self.application.data))
        self.finish()
      except IOError:
        pass
    else:
      self.application.callbacklist.append(self.ReturnData)

  def ReturnData(self):
    # print "checking if checksums are the same and print them if not"
    # print self.returndata
    # if not self.connection_closed:
    # print oldchecksum
    # print newchecksum
    # print "--------------------"
    if self.oldchecksum != self.application.newchecksum:
      # print oldchecksum
      # print newchecksum
      self.application.callbacklist.remove(self.ReturnData)
      try:
        self.set_header('Content-Type', 'text/javascript')
        self.write(tornado.escape.json_encode(self.application.data))
        self.finish()
      except IOError:
        pass


class DiaguiSettings(tornado.web.Application):
  """Defines settings for the server and notifier."""

  def __init__(self):
    self.settings = {
        'static_path': 'static',
        'template_path': '.',
    }
    super(DiaguiSettings, self).__init__([
        (r'/', MainHandler),
        (r'/diagnostics', DiagnosticsHandler),
        (r'/content.json', JsonHandler),
    ], **self.settings)

    self.ioloop = tornado.ioloop.IOLoop.instance()
    self.wm = tr.pyinotify.WatchManager()
    self.mask = tr.pyinotify.IN_CLOSE_WRITE
    self.callbacklist = []
    self.notifier = tr.pyinotify.TornadoAsyncNotifier(
        self.wm, self.ioloop, callback=self.AlertNotifiers)
    self.wdd = self.wm.add_watch('./Testdata', self.mask)
    self.GetLatestDict()

  def AlertNotifiers(self, notifier):
    self.GetLatestDict()
    for i in self.callbacklist[:]:
      i()

  def GetLatestDict(self):
    f = open('Testdata/testdata')
    self.data = dict(line.decode('utf-8').strip().split(None, 1) for line in f)
    self.newchecksum = hashlib.sha1(unicode(
        sorted(list(self.data.items()))).encode('utf-8')).hexdigest()
    self.data['checksum'] = self.newchecksum

