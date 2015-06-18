var SignalStrengthChart = function(ylabel, title, key, div_id, labels_div) {
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
  var dStart = new Date();
  this.curTime = dStart.getTime();
  this.initialized = false;
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
       xlabel: 'Time (s)',
       ylabel: this.ylabel
   });
};

/** Adds a point on the graph (with a time and an object that maps
  MAC addresses with signal strengths).
 * @param {int} time - we need time for the x axis of the dygraph, in seconds
 * @param {Object} sig_point - MAC addresses and signal strengths mapping
*/
SignalStrengthChart.prototype.addPoint = function(time, sig_point) {
  var numNewKeys = Object.keys(sig_point).length;
  console.log('num new keys ' + numNewKeys);

  var pointToAdd = [time];
  for (var mac_addr_index in Object.keys(sig_point)) {
    var mac_addr = (Object.keys(sig_point))[mac_addr_index];
    var index = this.listOfDevices.get(mac_addr);
    console.log('mac_addr=' + mac_addr + ' --> index=' + index);
    pointToAdd[index + 1] = sig_point[mac_addr];
    console.log(sig_point[mac_addr]);
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
  console.log(this.signalStrengths);
};

/** Gets data from JSON page and updates dygraph.
*/
SignalStrengthChart.prototype.getData = function() {
  var self = this;
  $.getJSON('/content.json?checksum=42', function(data) {
    var d = new Date();
    var time = d.getTime() / 1000 - self.curTime / 1000; // so it's not big
    self.addPoint(time, data[self.key]);
    var host_names = self.listOfDevices.hostNames(data['host_names']);
    if (!self.initialized) {
      self.initializeDygraph();
      self.initialized = true;
    }
    else {
      self.g.updateOptions({file: self.signalStrengths,
        labels: ['time'].concat(host_names)
        });
    }
    showData('#host_names', data['host_names'], 'Host Name');
    showData('#bitloading', data['moca_bitloading'], 'Bitloading');
    showBitloading(data['moca_bitloading']);
    $('#softversion').html($('<div/>').text(data['softversion']).html());
  });
  setTimeout(function() {
    self.getData();
  }, 1000);
};

function showData(div, data, dataName) {
  var nameString = '';
  for (var mac_addr in data) {
    if (data[mac_addr] != '') {
      nameString += '<p> MAC Address: ' +
       $('<div/>').text(mac_addr).html() + ', ' + dataName + ': ' +
       $('<div/>').text(data[mac_addr]).html() + '</p>';
    }
    else {
      nameString += '<p> MAC Address: ' +
       $('<div/>').text(mac_addr).html() + '</p>';
    }
  }
  $(div).html(nameString);
}

function showBitloading(data) {
  var prefix = '$BRCM2$';
  $('#bit_table').html('');
  for (var mac_addr in data) {
    var bitloading = data[mac_addr];
    for (var i = prefix.length; i < bitloading.length; i++) {
      if (bitloading[i] < 5) {
        $('#bit_table').append('<a style="background-color:#FF4136">' +
        bitloading[i] + '</a>');
      }
      else if (bitloading[i] < 7) {
        $('#bit_table').append('<a style="background-color:#FFDC00">' +
        bitloading[i] + '</a>');
      }
      else {
        $('#bit_table').append('<a style="background-color:#2ECC40">' +
        bitloading[i] + '</a>');
      }
    }
    $('#bit_table').append('<br style="clear:both"><br>');
  }
}
