#!/usr/bin/python
#
"""Implementation of the read-only Diagnostics UI."""

__author__ = 'anandkhare@google.com (Anand Khare)'

import hashlib
import os
import google3
import tornado.ioloop
import tornado.web
import tr.pyinotify


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

  @tornado.web.asynchronous
  def get(self):    # pylint: disable=g-bad-name
    if self.get_argument('checksum') != self.application.data['checksum']:
      try:
        self.set_header('Content-Type', 'text/javascript')
        self.write(tornado.escape.json_encode(self.application.data))
        self.finish()
      except IOError:
        pass
    else:
      self.application.callbacklist.append(self.ReturnData)

  def ReturnData(self):
    if self.get_argument('checksum') != self.application.data['checksum']:
      self.application.callbacklist.remove(self.ReturnData)
      try:
        self.set_header('Content-Type', 'text/javascript')
        self.write(tornado.escape.json_encode(self.application.data))
        self.finish()
      except IOError:
        pass


class RestartHandler(tornado.web.RequestHandler):
  """Restart the network box."""

  def get(self):    # pylint: disable=g-bad-name
    self.render('restarting.html')

  def post(self):    # pylint: disable=g-bad-name
    self.redirect('/restart')
    os.system('(sleep 5; reboot) &')


class DiaguiSettings(tornado.web.Application):
  """Defines settings for the server and notifier."""

  def __init__(self, root):
    self.root = root
    self.pathname = os.path.dirname(__file__)
    staticpath = os.path.join(self.pathname, 'static')
    self.UpdateLatestDict()
    self.settings = {
        'static_path': staticpath,
        'template_path': self.pathname,
        'xsrf_cookies': True,
    }
    super(DiaguiSettings, self).__init__([
        (r'/', MainHandler),
        (r'/diagnostics', DiagnosticsHandler),
        (r'/content.json', JsonHandler),
        (r'/restart', RestartHandler),
    ], **self.settings)

    self.ioloop = tornado.ioloop.IOLoop.instance()
    self.wm = tr.pyinotify.WatchManager()
    self.mask = tr.pyinotify.IN_CLOSE_WRITE
    self.callbacklist = []
    self.notifier = tr.pyinotify.TornadoAsyncNotifier(
        self.wm, self.ioloop, callback=self.AlertNotifiers)
    self.wdd = self.wm.add_watch(
        os.path.join(self.pathname, 'Testdata'), self.mask)

  def AlertNotifiers(self, notifier):
    self.UpdateLatestDict()
    for i in self.callbacklist[:]:
      i()

  def UpdateLatestDict(self):
    f = open(os.path.join(self.pathname, 'Testdata/testdata'))
    self.data = dict(line.decode('utf-8').strip().split(None, 1) for line in f)
    if self.root:
      deviceinfo = self.root.Device.DeviceInfo
      self.data['softversion'] = deviceinfo.SoftwareVersion
      self.data['uptime'] = deviceinfo.UpTime
      self.data['username'] = self.root.Device.ManagementServer.Username
      tempstatus = deviceinfo.TemperatureStatus
      t = dict()
      try:
        for i, sensor in tempstatus.TemperatureSensorList.iteritems():
          t[sensor.Name] = sensor.Value
        self.data['temperature'] = t
      except AttributeError:
        pass
      t = dict()
      for i, interface in self.root.Device.Ethernet.InterfaceList.iteritems():
        t[interface.MACAddress] = interface.Status
      self.data['wiredlan'] = t
      x = self.root.InternetGatewayDevice.LANDeviceList
      t = dict()
      for i, landevice in x.iteritems():
        for j, wlanconfig in landevice.WLANConfigurationList.iteritems():
          t[wlanconfig.BSSID] = wlanconfig.Status
      self.data['wirelesslan'] = t
    newchecksum = hashlib.sha1(unicode(
        sorted(list(self.data.items()))).encode('utf-8')).hexdigest()
    self.data['checksum'] = newchecksum

