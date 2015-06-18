var SignalStrengthChart = function(ylabel, title, key, div_id) {
  this.title = title;
  this.ylabel = ylabel;
  this.key = key;
  this.element = div_id;
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
    for (var i = 0; i < pointToAdd.length -
      this.signalStrengths[0].length; i++) {
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
        labels: ['time'].concat(host_names)});
    }
    // prints the mac address -> host name mappings
    var nameString = '';
    for (var mac_addr in data['host_names']) {
      if (data['host_names'][mac_addr] != '') {
        nameString += '<p> MAC Address: ' +
         $('<div/>').text(mac_addr).html() + ', Host Name: ' +
         $('<div/>').text(data['host_names'][mac_addr]).html() + '</p>';
      }
      else {
        nameString += '<p> MAC Address: ' +
         $('<div/>').text(mac_addr).html() + '</p>';
      }
    }
    $('#host_names').html(nameString);
  });
  setTimeout(function() {
    self.getData();
  }, 1000);
};
