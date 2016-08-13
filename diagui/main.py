#!/usr/bin/python
#
"""Implementation of the read-only Diagnostics UI."""

__author__ = 'anandkhare@google.com (Anand Khare)'

import datetime
import errno
import hashlib
import json
import mimetypes
import os

import google3

import tornado.web
import tr.cwmptypes
import tr.helpers
import tr.mainloop
import tr.pyinotify


# For unit test overrides.
ONU_STAT_FILE = '/tmp/cwmp/monitoring/onu/onustats.json'
ACTIVEWAN = 'activewan'
AP_DIR = '/tmp/waveguide/signals_json'
SELFSIGNALS_FILE = '/tmp/waveguide/signals_json/self_signals'
APSIGNAL_FILE = '/tmp/waveguide/signals_json/ap_signals'
SOFTWARE_VERSION_FILE = '/etc/version'
MOCAGLOBALJSON = '/tmp/cwmp/monitoring/moca2/globals'
JSON_DEADLINE = 1


def IOLoop():
  return tr.mainloop.IOLoopWrapper.instance()


def JsonGet(page, ui, update_dictionary):
  """Handle a request to get a new version of a dict when it's available.

  Args:
      page: A RequestHandler instance for the request being handled.
      ui: The TechUI or DiagUI instance that the request is for.  Must have a
          'data' attribute with a 'checksum' key; this is how we determine when
          to reply with a new version of the dictonary.  The 'data' attribute is
          serialized to JSON and sent as the response when ready.
      update_dictionary: A function that will update ui.data with the latest
          information.
  """
  page.ui = ui
  update_dictionary()
  if (page.get_argument('checksum') !=
      ui.data.get('checksum', None)):
    page.set_header('Content-Type', 'application/json')
    page.write(json.dumps(ui.data))
    page.finish()
  else:
    def Send(deadline_exceeded):
      """Called by the cwmp watchers when they think new data might be ready.

      The data might not actually be updated; in that case, we don't send.

      Args:
          deadline_exceeded: True if the timeout for answering the request has
              arrived.  In that case, we send whatever we have.
      """
      if (not deadline_exceeded and
          page.get_argument('checksum') == ui.data['checksum']):
        # callback called, but data didn't change, so do nothing.
        return

      page.ClearCallbacks()
      page.set_header('Content-Type', 'application/json')
      page.write(json.dumps(ui.data))
      page.finish()

    page.callback = lambda: Send(False)
    page.deadline = IOLoop().add_timeout(
        datetime.timedelta(seconds=JSON_DEADLINE), lambda: Send(True))
    ui.callbacklist.append(page.callback)


class _JsonHandler(tornado.web.RequestHandler):
  """Base class for handlers that serve async json files."""

  def initialize(self):
    self.ui = None
    self.callback = None
    self.deadline = None

  def ClearCallbacks(self):
    if self.deadline:
      dl = self.deadline
      self.deadline = None
      IOLoop().remove_timeout(dl)
    if self.callback:
      cb = self.callback
      self.callback = None
      self.ui.callbacklist.remove(cb)

  def on_connection_close(self):
    self.ClearCallbacks()


class TechUIJsonHandler(_JsonHandler):
  """Provides JSON-formatted info for the TechUI."""

  @tornado.web.asynchronous
  def get(self):
    print 'techui GET JSON data for diagnostics page'
    JsonGet(self, self.application.techui,
            self.application.techui.UpdateTechUIDict)


class TechUIHandler(tornado.web.RequestHandler):
  """Display technical UI."""

  def get(self):
    self.render('techui_static/index.html')


class StartIsostreamHandler(tornado.web.RequestHandler):
  """Sends requests to start isostream client on all TV boxes."""

  @tornado.web.asynchronous
  def post(self):
    self.outstanding_requests = 0
    self.request_results = {}
    tv_ip_addrs = self.application.techui.FindTVBoxes()
    for ip_addr in tv_ip_addrs:
      http_client = tornado.httpclient.AsyncHTTPClient()
      request = tornado.httpclient.HTTPRequest(
          url=ip_addr + '/isostream',
          method='POST', body='',
          request_timeout=2,
          headers={
              'Cookie': '_xsrf=q',
              'X-Csrftoken': 'q'
          })
      http_client.fetch(
          request, self.make_request_handler(ip_addr))
      self.outstanding_requests += 1

  def make_request_handler(self, ip_addr):
    return lambda response: self.handle_request(ip_addr, response)

  def handle_request(self, host, response):
    try:
      response.rethrow()
      self.request_results[host] = 'SUCCESS'
    except tornado.httpclient.HTTPError as e:
      self.request_results[host] = (
          'ERROR: %s' % e.code)
    finally:
      self.outstanding_requests -= 1
      if self.outstanding_requests == 0:
        self.write(self.request_results)
        self.finish()


class IsostreamHandler(tornado.web.RequestHandler):
  """Starts isostream client (usually on TV box)."""

  def post(self):
    print ('Starting isostream due to incoming request from %s'
           % self.request.remote_ip)
    isostreaminfo = (self.application.root.Device.IP.Diagnostics
                     .X_CATAWAMPUS_ORG_Isostream)
    isostreaminfo.last_log = None
    isostreaminfo.ClientRemoteIP = self.request.remote_ip
    isostreaminfo.ClientMbps = 14
    isostreaminfo.ClientEnable = True


class IsostreamJsonHandler(_JsonHandler):
  """Provides JSON of the last line of the isostream log (usually on TV box)."""

  @tornado.web.asynchronous
  def get(self):
    self.set_header('Content-Type', 'application/json')
    isostreaminfo = (self.application.root.Device.IP.Diagnostics
                     .X_CATAWAMPUS_ORG_Isostream)
    isos_dict = {}
    last_log_dict = {}
    if isostreaminfo.last_log:
      last_log_dict = vars(isostreaminfo.last_log)
    isos_dict['last_log'] = last_log_dict
    isos_dict['ClientRunning'] = isostreaminfo.ClientRunning
    self.write(json.dumps(isos_dict))
    try:
      self.finish()
    except IOError:
      # Other end already closed the connection. Not an error.
      pass


class IsostreamCombinedHandler(tornado.web.RequestHandler):
  """Gathers isostream JSON data from each connected TV box.

  This is usually run on the network box.
  """

  @tornado.web.asynchronous
  def get(self):
    self.outstanding_requests = 0
    self.combined_data = {}
    tv_ip_addrs = self.application.techui.FindTVBoxes()
    for ip_addr in tv_ip_addrs:
      http_client = tornado.httpclient.AsyncHTTPClient()
      request = tornado.httpclient.HTTPRequest(
          url=ip_addr + '/isostream.json',
          method='GET',
          request_timeout=1
          )
      http_client.fetch(
          request, self.make_request_handler(ip_addr))
      self.outstanding_requests += 1

  def make_request_handler(self, ip_addr):
    return lambda response: self.handle_request(ip_addr, response)

  def handle_request(self, host, response):
    try:
      response.rethrow()
      self.combined_data[host] = (
          json.loads(response.body))
    except tornado.httpclient.HTTPError as he:
      self.combined_data[host] = {
          'Error': 'HTTPError: %s' % str(he)
      }
    except TypeError as te:
      self.combined_data[host] = {
          'Error': 'TypeError: %s unable to parse %s' % (str(te), response.body)
      }
    finally:
      self.outstanding_requests -= 1
      if self.outstanding_requests == 0:
        self.write(self.combined_data)
        self.finish()


class DiagUIJsonHandler(_JsonHandler):
  """Provides JSON-formatted content to be displayed in the UI."""

  @tornado.web.asynchronous
  def get(self):
    print 'diagui GET JSON data for diagnostics page'
    JsonGet(self, self.application.diagui,
            self.application.diagui.UpdateDiagUIDict)


class DiagnosticsHandler(tornado.web.RequestHandler):
  """Displays the diagnostics UI."""

  def get(self):
    print 'diagui GET diagnostics HTML page'
    self.render('template.html', run_techui=self.application.run_techui)


class DiagUIRestartHandler(tornado.web.RequestHandler):
  """Restart the network box."""

  def get(self):
    print 'diagui displaying restart interstitial screen'
    self.render('restarting.html')

  def post(self):
    print 'diagui user requested restart'
    self.redirect('/restart')
    os.system('(sleep 5; reboot) &')


def LoadJson(filename):
  try:
    return json.loads(open(filename).read())
  except ValueError:
    return {}  # No json to read
  except IOError as e:
    if e.errno == errno.ENOENT:
      return {}  # file doesn't exist, harmless
    raise


class TechUI(object):
  """Class for the technical UI."""

  def __init__(self, root):
    self.data = {'wifi_signal_strength': {},
                 'moca_signal_strength': {},
                 'moca_corrected_codewords': {},
                 'moca_uncorrected_codewords': {},
                 'moca_bitloading': {},
                 'moca_nbas': {},
                 'other_aps': {},
                 'self_signals': {},
                 'host_names': {},
                 'ip_addr': {},
                 'softversion': '',
                 'serialnumber': '',
                 'checksum': 0}

    self.callbacklist = []
    self.root = root
    if self.root:
      for interface in self.root.Device.MoCA.InterfaceList.itervalues():
        tr.cwmptypes.AddNotifier(type(interface),
                                 'AssociatedDeviceCount',
                                 lambda _: self.UpdateMocaDict())
      landevlist = self.root.InternetGatewayDevice.LANDeviceList
      for dev in landevlist.itervalues():
        for wlconf in dev.WLANConfigurationList.itervalues():
          tr.cwmptypes.AddNotifier(type(wlconf),
                                   'SignalsStr',
                                   lambda _: self.UpdateWifiDict())
    mask = tr.pyinotify.IN_MODIFY
    self.ap_wm = tr.pyinotify.WatchManager()
    self.ap_notifier = tr.pyinotify.TornadoAsyncNotifier(
        self.ap_wm, IOLoop(), callback=lambda _: self.UpdateAPDict())
    if os.path.exists(AP_DIR):
      self.ap_wm.add_watch(AP_DIR, mask)

  def SetTechUIDict(self, key, new_dict):
    if key not in self.data:
      self.data[key] = new_dict
      return True
    if self.data[key] != new_dict:
      self.data[key] = new_dict
      return True
    return False

  def UpdateMocaDict(self):
    """Updates the dictionary with Moca data from catawampus."""
    updated = False
    snr = {}
    bitloading = {}
    corrected_cw = {}
    uncorrected_cw = {}
    nbas = {}

    global_content = LoadJson(MOCAGLOBALJSON)
    global_node_id = global_content.get('NodeId', 17)  # max nodes is 16
    for interface in self.root.Device.MoCA.InterfaceList.itervalues():
      for dev in interface.AssociatedDeviceList.itervalues():
        if dev.NodeID != global_node_id:  #  to avoid getting info about self
          snr[dev.MACAddress] = dev.X_CATAWAMPUS_ORG_RxSNR_dB
          bitloading[dev.MACAddress] = dev.X_CATAWAMPUS_ORG_RxBitloading
          nbas[dev.MACAddress] = dev.X_CATAWAMPUS_ORG_RxNBAS
          corrected = (dev.X_CATAWAMPUS_ORG_RxPrimaryCwCorrected +
                       dev.X_CATAWAMPUS_ORG_RxSecondaryCwCorrected)
          uncorrected = (dev.X_CATAWAMPUS_ORG_RxPrimaryCwUncorrected +
                         dev.X_CATAWAMPUS_ORG_RxSecondaryCwUncorrected)
          no_errors = (dev.X_CATAWAMPUS_ORG_RxPrimaryCwNoErrors +
                       dev.X_CATAWAMPUS_ORG_RxSecondaryCwNoErrors)
          total = corrected + uncorrected + no_errors
          if total != 0:
            corrected_cw[dev.MACAddress] = corrected/total
            uncorrected_cw[dev.MACAddress] = uncorrected/total
          else:
            corrected_cw[dev.MACAddress] = 0
            uncorrected_cw[dev.MACAddress] = 0
    updated = self.SetTechUIDict('moca_signal_strength', snr)
    updated = self.SetTechUIDict('moca_corrected_codewords',
                                 corrected_cw) or updated
    updated = self.SetTechUIDict('moca_uncorrected_codewords',
                                 uncorrected_cw) or updated
    updated = self.SetTechUIDict('moca_bitloading', bitloading) or updated
    updated = self.SetTechUIDict('moca_nbas', nbas) or updated
    if updated:
      self.NotifyUpdatedDict()

  def UpdateWifiDict(self):
    """Updates the wifi signal strength dict using catawampus."""
    wifi_signal_strengths = {}
    landevlist = self.root.InternetGatewayDevice.LANDeviceList
    for dev in landevlist.itervalues():
      for wlconf in dev.WLANConfigurationList.itervalues():
        wifi_signal_strengths.update(wlconf.signals)
    if self.SetTechUIDict('wifi_signal_strength', wifi_signal_strengths):
      self.NotifyUpdatedDict()

  def UpdateAPDict(self):
    """Reads JSON from the access points files and updates the dict."""
    # TODO(theannielin): waveguide data should be in cwmp, but it's not,
    # so we read it here
    updated = False
    other_aps = LoadJson(APSIGNAL_FILE)
    self_signals = LoadJson(SELFSIGNALS_FILE)
    updated = self.SetTechUIDict('other_aps', other_aps)
    updated = self.SetTechUIDict('self_signals', self_signals) or updated
    if updated:
      self.NotifyUpdatedDict()

  def UpdateTechUIDict(self):
    """Updates the data dictionary."""

    if not self.root:
      return

    host_names = {}
    ip_addr = {}

    try:
      hostinfo = self.root.Device.Hosts.HostList
    except AttributeError:
      hostinfo = {}

    for host in hostinfo.itervalues():
      host_names[host.PhysAddress] = host.HostName
      ip_addr[host.PhysAddress] = host.IPAddress

    self.data['host_names'] = host_names
    self.data['ip_addr'] = ip_addr

    deviceinfo = self.root.Device.DeviceInfo
    self.data['softversion'] = deviceinfo.SoftwareVersion
    self.data['serialnumber'] = deviceinfo.SerialNumber

    self.UpdateMocaDict()
    self.UpdateWifiDict()
    self.UpdateAPDict()
    self.UpdateCheckSum()

  def NotifyUpdatedDict(self):
    self.UpdateCheckSum()
    for i in self.callbacklist[:]:
      i()

  def UpdateCheckSum(self):
    self.data['checksum'] = 0
    newchecksum = hashlib.sha1(unicode(
        sorted(list(self.data.items()))).encode('utf-8')).hexdigest()
    self.data['checksum'] = 'sha1%s' % newchecksum

  def FindTVBoxes(self):
    tv_ip_addrs = []
    if 'host_names' in self.data:
      for mac_addr, host_name in self.data['host_names'].iteritems():
        if host_name.startswith('GFiberTV'):
          tv_ip_addrs.append(self.data['ip_addr'][mac_addr])
    return tv_ip_addrs


class DiagUI(object):
  """Class for the diagnostics UI."""

  def __init__(self, root, cpemach):
    self.data = {}
    self.root = root
    self.cpemach = cpemach
    self.pathname = os.path.dirname(__file__)
    if self.root:
      # TODO(anandkhare): Add notifiers on more parameters using the same format
      # as below, as and when they are implemented using types.py.
      tr.cwmptypes.AddNotifier(type(self.root.Device.Ethernet),
                               'InterfaceNumberOfEntries', self.AlertNotifiers)
    self.wm = tr.pyinotify.WatchManager()
    self.mask = tr.pyinotify.IN_CLOSE_WRITE
    self.callbacklist = []
    self.notifier = tr.pyinotify.TornadoAsyncNotifier(
        self.wm, IOLoop(), callback=self.AlertNotifiers)
    self.wdd = self.wm.add_watch(
        os.path.join(self.pathname, 'Testdata'), self.mask)

  def AlertNotifiers(self, unused_obj):
    self.UpdateDiagUIDict()
    for i in self.callbacklist[:]:
      i()

  def UpdateCheckSum(self):
    self.data['checksum'] = 0
    newchecksum = hashlib.sha1(unicode(
        sorted(list(self.data.items()))).encode('utf-8')).hexdigest()
    self.data['checksum'] = newchecksum

  def UpdateDiagUIDict(self):
    """Updates the dictionary and checksum value."""

    if not self.root:
      return

    self.data = {}
    self.data['subnetmask'] = ''

    deviceinfo = self.root.Device.DeviceInfo
    tempstatus = deviceinfo.TemperatureStatus
    landevlist = self.root.InternetGatewayDevice.LANDeviceList
    etherlist = self.root.Device.Ethernet.InterfaceList

    if self.cpemach and self.cpemach.last_success_response:
      self.data['acs'] = 'OK (%s)' % self.cpemach.last_success_response
    else:
      self.data['acs'] = 'Never contacted'
    self.data['softversion'] = deviceinfo.SoftwareVersion
    self.data['serialnumber'] = deviceinfo.SerialNumber
    self.data['uptime'] = deviceinfo.UpTime

    t = dict()
    try:
      for sensor in tempstatus.TemperatureSensorList.itervalues():
        t[sensor.Name] = sensor.Value
    except AttributeError:
      pass
    else:
      self.data['temperature'] = t

    wan_addrs = dict()
    lan_addrs = dict()
    for inter in self.root.Device.IP.InterfaceList.itervalues():
      t = wan_addrs if inter.Name in ['wan0', 'wan0.2'] else lan_addrs
      for ip4 in inter.IPv4AddressList.itervalues():
        # Static IPs show up even if there is no address.
        if ip4.IPAddress is not None:
          t[ip4.IPAddress] = '(%s)' % ip4.Status
          self.data['subnetmask'] = ip4.SubnetMask
      for ip6 in inter.IPv6AddressList.itervalues():
        if ip6.IPAddress[:4] != 'fe80':
          t[ip6.IPAddress] = '(%s)' % ip6.Status
    self.data['lanip'] = lan_addrs
    self.data['wanip'] = wan_addrs

    wan_mac = dict()
    lan_mac = dict()
    t = dict()
    for interface in etherlist.itervalues():
      if interface.Name in ['wan0', 'wan0.2']:
        wan_mac[interface.MACAddress] = '(%s)' % interface.Status
      else:
        lan_mac[interface.MACAddress] = '(%s)' % interface.Status
    self.data['lanmac'] = lan_mac
    self.data['wanmac'] = wan_mac

    wlan = dict()
    wpa = dict()
    self.data['ssid5'] = ''

    for dev in landevlist.itervalues():
      for wlconf in dev.WLANConfigurationList.itervalues():
        # Convert the channel to an int here.  It is returned as a string.
        try:
          ch = int(wlconf.Channel)
        except ValueError:
          print ('wlconf.Channel returned a non-integer value: %s' %
                 (wlconf.Channel,))
          continue

        if ch in range(1, 12):
          self.data['ssid24'] = wlconf.SSID
          if wlconf.WPAAuthenticationMode == 'PSKAuthentication':
            wpa['2.4 GHz'] = '(Configured)'
          wlan[wlconf.BSSID] = '(2.4 GHz) (%s)' % wlconf.Status
        else:
          self.data['ssid5'] = wlconf.SSID
          if wlconf.WPAAuthenticationMode == 'PSKAuthentication':
            wpa['5 GHz'] = '(Configured)'
          wlan[wlconf.BSSID] = '(5 GHz) (%s)' % wlconf.Status

    self.data['wirelesslan'] = wlan
    self.data['wpa2'] = wpa

    if 'ssid24' in self.data and 'ssid5' in self.data:
      if self.data['ssid5'] == self.data['ssid24']:
        self.data['ssid5'] = '(same)'

    try:
      self.data['upnp'] = self.root.UPnP.Device.Enable
    except AttributeError:
      self.data['upnp'] = 'Off'

    try:
      dns = self.root.DNS.SD.ServiceList
    except AttributeError:
      pass
    else:
      for serv in dns.itervalues():
        self.data['dyndns'] = serv.InstanceName
        self.data['domain'] = serv.Domain

    # We want the 'connected' field to be a boolean, but Activewan
    # returns either the empty string, or the name of the active wan
    # interface.
    self.data['connected'] = not not tr.helpers.Activewan(ACTIVEWAN)

    self.ReadOnuStats()
    self.UpdateCheckSum()

  def ReadOnuStats(self):
    """Read the ONU stat file and store into self.data."""
    try:
      stats = open(ONU_STAT_FILE).read()
    except IOError as e:
      if e.errno != errno.ENOENT:
        print 'Failed to read onu stat file: %s' % e
      return

    try:
      json_stats = json.loads(stats)
    except ValueError as e:
      print 'Failed to decode onu stat file: %s' % e
      return

    self.data.update(json_stats)


class MainApplication(tornado.web.Application):
  """Defines settings for the server and notifier."""

  def __init__(self, root, cpemach, run_techui=False):
    self.root = root
    self.diagui = DiagUI(root, cpemach)
    self.run_techui = run_techui
    self.techui = TechUI(root)
    self.pathname = os.path.dirname(__file__)
    staticpath = os.path.join(self.pathname, 'static')
    self.settings = {
        'static_path': staticpath,
        'template_path': self.pathname,
        'xsrf_cookies': True,
    }

    handlers = [
        (r'/', DiagnosticsHandler),
        (r'/content.json', DiagUIJsonHandler),
        (r'/restart', DiagUIRestartHandler),
    ]

    if run_techui:
      handlers += [
          (r'/tech/?', tornado.web.RedirectHandler,
           {'url': '/tech/index.html'}),
          (r'/tech/index.html', TechUIHandler),
          (r'/tech/(.*)', tornado.web.StaticFileHandler,
           {'path': os.path.join(self.pathname, 'techui_static')}),
          (r'/techui.json', TechUIJsonHandler),
          (r'/startisostream', StartIsostreamHandler),
          (r'/isostream', IsostreamHandler),
          (r'/isostream.json', IsostreamJsonHandler),
          (r'/isostreamcombined.json', IsostreamCombinedHandler),
      ]

    super(MainApplication, self).__init__(handlers, **self.settings)
    mimetypes.add_type('font/ttf', '.ttf')
