#!/usr/bin/python
#
"""Implementation of the read-only Diagnostics UI."""

__author__ = 'anandkhare@google.com (Anand Khare)'

import hashlib
import json
import mimetypes
import os
import google3
import tornado.ioloop
import tornado.web
import tr.cwmptypes
import tr.helpers
import tr.pyinotify

# For unit test overrides.
ONU_STAT_FILE = '/tmp/cwmp/monitoring/onu/onustats.json'
ACTIVEWAN = 'activewan'
WIFISIGNAL_FILE = '/tmp/wifisignal'
MOCA_FILE = '/tmp/techuimocainfo'
MOCA_NODES_DIR = '/tmp/cwmp/monitoring/moca2'


class TechUIWifiJsonHandler(tornado.web.RequestHandler):
  """Provides JSON-formatted wifi content to be displayed in the TechUI."""

  def get(self):
    info = ''
    signal_strengths = {}
    if os.path.isfile(WIFISIGNAL_FILE):
      if not os.listdir('/tmp/stations'):
        signal_strengths['signal_strength'] = {}
        tr.helpers.WriteFileAtomic(WIFISIGNAL_FILE,
                                   json.dumps(signal_strengths))
      else:
        with open(WIFISIGNAL_FILE) as f:
          info = f.read()
    try:
      self.set_header('Content-Type', 'application/json')
      self.write(info)
      self.finish()
    except IOError:
      pass


class TechUIMoCAJsonHandler(tornado.web.RequestHandler):
  """Provides JSON-formatted MoCA content to be displayed in the TechUI."""

  def get(self):
    data = {}
    snr = {}
    bitloading = {}
    codewords = {}
    nbas = {}
    for node in os.listdir(MOCA_NODES_DIR):
      nodefile = os.path.join(MOCA_NODES_DIR, node)
      if os.path.isfile(nodefile) and node.startswith('node'):
        with open(nodefile) as f:
          node_content = json.loads(f.read())
          try:
            mac_addr = node_content['MACAddress']
            if mac_addr != '00:00:00:00:00:00':
              snr[mac_addr] = node_content['RxSNR']
              bitloading[mac_addr] = node_content['RxBitloading']
              nbas[mac_addr] = node_content['RxNBAS']
              corrected = (node_content['RxPrimaryCwCorrected'] +
                           node_content['RxSecondaryCwCorrected'])
              uncorrected = (node_content['RxPrimaryCwUncorrected'] +
                             node_content['RxSecondaryCwUncorrected'])
              no_errors = (node_content['RxPrimaryCwNoErrors'] +
                           node_content['RxSecondaryCwNoErrors'])
              total = corrected + uncorrected + no_errors
              try:
                codewords['corrected' + mac_addr] = corrected/total
                codewords['uncorrected' + mac_addr] = uncorrected/total
              except ZeroDivisionError:
                codewords['corrected' + mac_addr] = 0
                codewords['uncorrected' + mac_addr] = 0
          except KeyError:
            pass
    data['moca_signal_strength'] = snr
    data['moca_codewords'] = codewords
    data['moca_bitloading'] = bitloading
    data['moca_nbas'] = nbas
    tr.helpers.WriteFileAtomic(MOCA_FILE, json.dumps(data))
    try:
      self.set_header('Content-Type', 'application/json')
      self.write(json.dumps(data))
      self.finish()
    except IOError:
      pass


class DiagnosticsHandler(tornado.web.RequestHandler):
  """If no connectivity, display local diagnostics UI."""

  def get(self):    # pylint: disable=g-bad-name
    print 'diagui GET diagnostics HTML page'
    self.render('template.html')


class JsonHandler(tornado.web.RequestHandler):
  """Provides JSON-formatted content to be displayed in the UI."""

  @tornado.web.asynchronous
  def get(self):    # pylint: disable=g-bad-name
    print 'diagui GET JSON data for diagnostics page'
    self.application.UpdateLatestDict()
    if (self.get_argument('checksum') !=
        self.application.data.get('checksum', None)):
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
    print 'diagui displaying restart interstitial screen'
    self.render('restarting.html')

  def post(self):    # pylint: disable=g-bad-name
    print 'diagui user requested restart'
    self.redirect('/restart')
    os.system('(sleep 5; reboot) &')


class DiaguiSettings(tornado.web.Application):
  """Defines settings for the server and notifier."""

  def __init__(self, root, cpemach, run_techui=False):
    self.data = {}
    self.root = root
    self.cpemach = cpemach

    if self.root:
      tr.cwmptypes.AddNotifier(type(self.root.Device.Ethernet),
                               'InterfaceNumberOfEntries', self.AlertNotifiers)

      # TODO(anandkhare): Add notifiers on more parameters using the same format
      # as above, as and when they are implemented using types.py.
    self.pathname = os.path.dirname(__file__)
    staticpath = os.path.join(self.pathname, 'static')
    self.settings = {
        'static_path': staticpath,
        'template_path': self.pathname,
        'xsrf_cookies': True,
    }

    handlers = [
        (r'/', DiagnosticsHandler),
        (r'/content.json', JsonHandler),
        (r'/restart', RestartHandler),
    ]

    if run_techui:
      handlers += [
          (r'/tech/?', tornado.web.RedirectHandler,
           {'url': '/tech/index.html'}),
          (r'/tech/(.*)', tornado.web.StaticFileHandler,
           {'path': os.path.join(self.pathname, 'techui_static')}),
          (r'/signal.json', TechUIWifiJsonHandler),
          (r'/moca.json', TechUIMoCAJsonHandler),
      ]

    super(DiaguiSettings, self).__init__(handlers, **self.settings)
    mimetypes.add_type('font/ttf', '.ttf')

    self.ioloop = tornado.ioloop.IOLoop.instance()
    self.wm = tr.pyinotify.WatchManager()
    self.mask = tr.pyinotify.IN_CLOSE_WRITE
    self.callbacklist = []
    self.notifier = tr.pyinotify.TornadoAsyncNotifier(
        self.wm, self.ioloop, callback=self.AlertNotifiers)
    self.wdd = self.wm.add_watch(
        os.path.join(self.pathname, 'Testdata'), self.mask)

  def AlertNotifiers(self, obj):
    self.UpdateLatestDict()
    for i in self.callbacklist[:]:
      i()

  def UpdateCheckSum(self):
    newchecksum = hashlib.sha1(unicode(
        sorted(list(self.data.items()))).encode('utf-8')).hexdigest()
    self.data['checksum'] = newchecksum

  def UpdateLatestDict(self):
    """Updates the dictionary and checksum value."""

    if not self.root:
      return

    self.data = {}
    self.data['subnetmask'] = ''

    deviceinfo = self.root.Device.DeviceInfo
    hostinfo = self.root.Device.Hosts.HostList
    tempstatus = deviceinfo.TemperatureStatus
    landevlist = self.root.InternetGatewayDevice.LANDeviceList
    etherlist = self.root.Device.Ethernet.InterfaceList

    if self.cpemach and self.cpemach.last_success_response:
      self.data['acs'] = 'OK (%s)' % self.cpemach.last_success_response
    else:
      self.data['acs'] = 'Never contacted'
    self.data['softversion'] = deviceinfo.SoftwareVersion
    self.data['uptime'] = deviceinfo.UpTime
    self.data['username'] = self.root.Device.ManagementServer.Username

    t = dict()
    try:
      for unused_i, sensor in tempstatus.TemperatureSensorList.iteritems():
        t[sensor.Name] = sensor.Value
      self.data['temperature'] = t
    except AttributeError:
      pass

    wan_addrs = dict()
    lan_addrs = dict()
    for unused_i, inter in self.root.Device.IP.InterfaceList.iteritems():
      t = wan_addrs if inter.Name in ['wan0', 'wan0.2'] else lan_addrs
      for unused_j, ip4 in inter.IPv4AddressList.iteritems():
        # Static IPs show up even if there is no address.
        if ip4.IPAddress is not None:
          t[ip4.IPAddress] = '(%s)' % ip4.Status
          self.data['subnetmask'] = ip4.SubnetMask
      for unused_i, ip6 in inter.IPv6AddressList.iteritems():
        if ip6.IPAddress[:4] != 'fe80':
          t[ip6.IPAddress] = '(%s)' % ip6.Status
    self.data['lanip'] = lan_addrs
    self.data['wanip'] = wan_addrs

    wan_mac = dict()
    lan_mac = dict()
    t = dict()
    for unused_i, interface in etherlist.iteritems():
      if interface.Name in ['wan0', 'wan0.2']:
        wan_mac[interface.MACAddress] = '(%s)' % interface.Status
      else:
        lan_mac[interface.MACAddress] = '(%s)' % interface.Status
    self.data['lanmac'] = lan_mac
    self.data['wanmac'] = wan_mac

    host_names = dict()
    for _, host in hostinfo.iteritems():
      host_names[host.PhysAddress] = host.HostName
    self.data['host_names'] = host_names

    t = dict()
    moca_signal_strength = dict()
    moca_bitloading = dict()
    moca_codewords = dict()
    for unused_i, inter in self.root.Device.MoCA.InterfaceList.iteritems():
      for unused_j, dev in inter.AssociatedDeviceList.iteritems():
        t[dev.NodeID] = dev.MACAddress
        moca_signal_strength[dev.MACAddress] = dev.X_CATAWAMPUS_ORG_RxSNR_dB
        moca_bitloading[dev.MACAddress] = dev.X_CATAWAMPUS_ORG_RxBitloading
        corrected = (dev.X_CATAWAMPUS_ORG_RxPrimaryCwCorrected +
                     dev.X_CATAWAMPUS_ORG_RxSecondaryCwCorrected)
        uncorrected = (dev.X_CATAWAMPUS_ORG_RxPrimaryCwUncorrected +
                       dev.X_CATAWAMPUS_ORG_RxSecondaryCwUncorrected)
        no_errors = (dev.X_CATAWAMPUS_ORG_RxPrimaryCwNoErrors +
                     dev.X_CATAWAMPUS_ORG_RxSecondaryCwNoErrors)
        total = corrected + uncorrected + no_errors
        try:
          moca_codewords['corrected' + dev.MACAddress] = corrected/total
          moca_codewords['uncorrected' + dev.MACAddress] = uncorrected/total
        except ZeroDivisionError:
          moca_codewords['corrected' + dev.MACAddress] = 0
          moca_codewords['uncorrected' + dev.MACAddress] = 0
    self.data['wireddevices'] = t
    self.data['moca_signal_strength'] = moca_signal_strength
    self.data['moca_bitloading'] = moca_bitloading
    self.data['moca_codewords'] = moca_codewords

    wlan = dict()
    devices = dict()
    signal_strength = dict()
    wpa = dict()
    self.data['ssid5'] = ''

    for unused_i, dev in landevlist.iteritems():
      for unused_j, wlconf in dev.WLANConfigurationList.iteritems():
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
          for unused_k, assoc in wlconf.AssociatedDeviceList.iteritems():
            devices[assoc.AssociatedDeviceMACAddress] = (
                '(2.4 GHz) (Authentication state: %s)'
                % assoc.AssociatedDeviceAuthenticationState)
            signal_strength[assoc.AssociatedDeviceMACAddress] = (
                assoc.X_CATAWAMPUS_ORG_SignalStrength
            )
        else:
          self.data['ssid5'] = wlconf.SSID
          if wlconf.WPAAuthenticationMode == 'PSKAuthentication':
            wpa['5 GHz'] = '(Configured)'
          wlan[wlconf.BSSID] = '(5 GHz) (%s)' % wlconf.Status
          for unused_k, assoc in wlconf.AssociatedDeviceList.iteritems():
            devices[assoc.AssociatedDeviceMACAddress] = (
                '(5 GHz) (Authentication state: %s)'
                % assoc.AssociatedDeviceAuthenticationState)
            signal_strength[assoc.AssociatedDeviceMACAddress] = (
                assoc.X_CATAWAMPUS_ORG_SignalStrength
            )

    self.data['wirelesslan'] = wlan
    self.data['wirelessdevices'] = devices
    self.data['wpa2'] = wpa
    self.data['signal_strength'] = signal_strength

    if 'ssid24' in self.data and 'ssid5' in self.data:
      if self.data['ssid5'] == self.data['ssid24']:
        self.data['ssid5'] = '(same)'

    try:
      self.data['upnp'] = self.root.UPnP.Device.Enable
    except AttributeError:
      self.data['upnp'] = 'Off'

    try:
      dns = self.root.DNS.SD.ServiceList
      for unused_i, serv in dns.iteritems():
        self.data['dyndns'] = serv.InstanceName
        self.data['domain'] = serv.Domain
    except AttributeError:
      pass

    # We want the 'connected' field to be a boolean, but Activewan
    # returns either the empty string, or the name of the active wan
    # interface.
    self.data['connected'] = not not tr.helpers.Activewan(ACTIVEWAN)

    self.ReadOnuStats()
    self.UpdateCheckSum()

  def ReadOnuStats(self):
    """Read the ONU stat file and store into self.data."""
    try:
      with open(ONU_STAT_FILE) as f:
        stats = f.read()
    except IOError:
      return

    try:
      json_stats = json.loads(stats)
    except ValueError:
      print 'Failed to decode onu stat file.'
      return

    self.data.update(json_stats)
