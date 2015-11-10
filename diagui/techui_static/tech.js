var SignalStrengthChart = function(ylabel, title, key, div_id,
                                   labels_div, is_moca) {
  this.title = title;
  this.ylabel = ylabel;
  this.key = key;
  this.element = div_id;
  this.labels_div = labels_div;
  this.signalStrengths = [];
  this.listOfDevices = new deviceList();
  this.g = null; /* The actual graph, initialized by
   initializeDygraph so that the chart doesn't have
   data until data is retrieved from the server. */
  this.initialized = false;
  this.is_moca = is_moca;
  return this;
};

/** Initializes a dygraph.
*/
SignalStrengthChart.prototype.initializeDygraph = function() {
  this.g = new Dygraph(document.getElementById(this.element),
   // For possible data formats, see http://dygraphs.com/data.html
   // The x-values could also be dates, e.g. '2012/03/15'
   this.signalStrengths,
   {
       // options go here. See http://dygraphs.com/options.html
       legend: 'always',
       animatedZooms: true,
       title: this.title,
       /* labels initialized with mac addr because host names may not be
       immediately available */
       labels: ['time'].concat(Object.keys(this.listOfDevices.devices)),
       labelsDiv: this.labels_div,
       xlabel: 'Time',
       ylabel: this.ylabel,
       axisLabelFontSize: 10
   });
};

/** Adds a point on the graph (with a time and an object that maps
  MAC addresses with signal strengths).
 * @param {Object} time - we need time (a date object) for the x axis
 * @param {Object} sig_point - MAC addresses and signal strengths mapping
*/
SignalStrengthChart.prototype.addPoint = function(time, sig_point) {
  var numNewKeys = Object.keys(sig_point).length;
  var pointToAdd = [time];
  for (var macAddr_index in Object.keys(sig_point)) {
    var macAddr = (Object.keys(sig_point))[macAddr_index];
    var index = this.listOfDevices.get(macAddr);
    pointToAdd[index + 1] = sig_point[macAddr];
  }

  if (this.signalStrengths.length > 0 &&
    pointToAdd.length > this.signalStrengths[0].length) {
    while (this.signalStrengths[0].length < pointToAdd.length) {
      for (var point = 0; point < this.signalStrengths.length; point++) {
        this.signalStrengths[point].push(null);
      }
    }
    if (this.initialized) {
      this.initializeDygraph();
    }
  }
  this.signalStrengths.push(pointToAdd);
};

var checksum = 0;

function checkData(data) {
  keys = ['wifi_signal_strength', 'wifiblaster_results', 'moca_signal_strength',
          'moca_corrected_codewords', 'moca_uncorrected_codewords',
          'moca_bitloading', 'moca_nbas', 'other_aps', 'self_signals',
          'host_names', 'ip_addr'];
  for (var index in keys) {
    key = keys[index];
    if (!(key in data)) {
      data[keys[index]] = {};
    }
  }
  if (!('checksum' in data)) {
    data['checksum'] = 0;
  }
  if (!('softversion' in data)) {
    data['softversion'] = '';
  }
}

/** Gets data from JSON page and updates dygraph.
 * @param {array} graph_array - graphs that need updates
*/
function getData(graph_array) {
  var payload = [];
  payload.push('checksum=' + encodeURIComponent(checksum));
  url = '/techui.json?' + payload.join('&');
  $.getJSON(url, function(data) {
    checkData(data);
    checksum = data['checksum'];
    for (var i = 0; i < graph_array.length; i++) {
      graph = graph_array[i];
      var time = new Date();
      graph.addPoint(time, data[graph.key]);
      var hostNames = {};
      if (graph.is_moca) {
        hostNames = graph.listOfDevices.mocaHostNames(data['host_names']);
      } else {
        hostNames = graph.listOfDevices.hostNames(data['host_names']);
      }

      var hostNamesArray = [];
      for (var macAddr in hostNames) {
        hostNamesArray.push(hostNames[macAddr]);
      }
      if (!graph.initialized) {
        if (graph.signalStrengths.length == 0) {
          graph.addPoint(time, {});
        }
        graph.initializeDygraph();
        graph.initialized = true;
      }
      else {
        graph.g.updateOptions({file: graph.signalStrengths,
          labels: ['time'].concat(hostNamesArray)});
      }
    }
    showDeviceTable('#device_info', data['host_names'], data['ip_addr']);
    showBitloading(data);
    $('#softversion').html($('<div/>').text(data['softversion']).html());
    // Send another request when the request succeeds
    getData(graph_array);
  });
}

function getIsostreamData(clientRunning) {
  var graphs = [offset, drops, disconn];
  if (!clientRunning) {
    for (var i in graphs) {
      graph = graphs[i];
      graph.signalStrengths = [];
    }
  }

  $.getJSON('/isostreamcombined.json', function(data) {
    var timestamp = 0;
    var offsetPoint = {};
    var dropsPoint = {};
    var disconnPoint = {};
    var ipAddrs = [];
    for (var ipAddr in data) {
      ipAddrs.push(ipAddr);
      if ('Error' in data[ipAddr]) {
          console.error(ipAddr + ': ' + data[ipAddr]['Error']);
      }
      if ('ClientRunning' in data[ipAddr]) {
        clientRunning = data[ipAddr]['ClientRunning'];
      }
      if ('last_log' in data[ipAddr] &&
          'timestamp' in data[ipAddr]['last_log']) {
        timestamp = Math.max(
          timestamp, data[ipAddr]['last_log']['timestamp']);
        offsetPoint[ipAddr] = data[ipAddr]['last_log']['offset'];
        dropsPoint[ipAddr] = data[ipAddr]['last_log']['drops'];
        disconnPoint[ipAddr] = data[ipAddr]['last_log']['disconn'];
      } else {
        offsetPoint[ipAddr] = null;
        dropsPoint[ipAddr] = null;
        disconnPoint[ipAddr] = null;
      }
    }

    offset.addPoint(timestamp, offsetPoint);
    drops.addPoint(timestamp, dropsPoint);
    disconn.addPoint(timestamp, disconnPoint);
    for (var i in graphs) {
      graph = graphs[i];
      if (!graph.initialized) {
        if (graph.signalStrengths.length == 0) {
          graph.addPoint(time, {});
        }
        graph.initializeDygraph();
        graph.initialized = true;
      } else {
        if (timestamp != 0) {
          graph.g.updateOptions({file: graph.signalStrengths,
            labels: ['time'].concat(ipAddrs)});
        }
      }
    }
    setTimeout(function() {
      if (clientRunning) {
        getIsostreamData(clientRunning);
      } else {
        $('#isos_status').append('Finished running tests.');
      }
    }, 1000);
  });
}

function showDeviceTable(div, hostNames, ipAddr) {
  var infoString = ('<table><tr><td><b>MAC Address</b></td><td><b>Host Name' +
                    '</b></td><td><b>IP Address</b></td></tr>');
  for (var macAddr in hostNames) {
    escapedMacAddr = $('<div/>').text(macAddr).html();
    infoString += '<tr><td>' + escapedMacAddr + '</td>';
    if (hostNames[macAddr] != '') {
      escapedHostName = $('<div/>').text(hostNames[macAddr]).html();
      infoString += '<td>' + escapedHostName + '</td>';
    }
    else {
      infoString += '<td></td>';
    }
    if (ipAddr[macAddr] != '') {
      escapedIpAddr = $('<div/>').text(ipAddr[macAddr]).html();
      infoString += '<td>' + escapedIpAddr + '</td>';
    }
    else {
      infoString += '<td></td>';
    }
    infoString += '</tr>';
  }
  infoString += '</table>';
  $(div).html(infoString);
}

function showBitloading(data) {
  var bit_data = data['moca_bitloading'];
  var nbas = data['moca_nbas'];
  var prefix = '$BRCM2$';
  $('#bitloading').html('');
  for (var macAddr in bit_data) {
    $('#bitloading').append('<span>Bitloading: ' + macAddr + '</span><br>');
    $('#bitloading').append('<span>NBAS: ' + nbas[macAddr] + '</span><br>');
    var bitloading = bit_data[macAddr];
    for (var i = prefix.length; i < bitloading.length; i++) {
      var bl = parseInt(bitloading[i], 16);
      var chan = i - prefix.length;
      var color;

      if (isNaN(bl)) {
        console.log('Could not parse', bitloading[i], 'as a number.');
        continue;
      }
      if ((chan < 4) || (chan > 243 && chan < 269) || (chan > 508)) {
        /** Guard bands. */
        color = '#E5E5E5';
      } else if (bl < 5) {
        color = '#FF4136';
      } else if (bl < 7) {
        color = '#FFDC00';
      } else {
        color = '#2ECC40';
      }

      $('#bitloading').append('<span class="bit" ' +
        'style="background-color:' + color + '">' + bitloading[i] + '</span>');
    }
    $('#bitloading').append('<br style="clear:both"><br>');
  }
}
