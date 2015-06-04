var g;
var signal_strengths = [];
var dStart = new Date();
var curTime = dStart.getTime();
var listOfDevices = new deviceList();
var initialized = false;

function initializeDygraph() {
  g = new Dygraph(document.getElementById('graph'),
   // For possible data formats, see http://dygraphs.com/data.html
   // The x-values could also be dates, e.g. "2012/03/15"
   signal_strengths,
   {
       // options go here. See http://dygraphs.com/options.html
       legend: 'always',
       animatedZooms: true,
       title: 'RSSI'
   });

}

function addPoint(time, sig_point) {
  var numNewKeys = Object.keys(sig_point).length;
  console.log('num new keys ' + numNewKeys);

  var pointToAdd = [time];
  for (var mac_addr_index in Object.keys(sig_point)) {
    var mac_addr = (Object.keys(sig_point))[mac_addr_index];
    var index = listOfDevices.get(mac_addr);
    console.log('mac_addr=' + mac_addr + ' --> index=' + index);
    pointToAdd[index + 1] = sig_point[mac_addr];
    console.log(sig_point[mac_addr]);
  }

  if (signal_strengths.length > 0 &&
    pointToAdd.length > signal_strengths[0].length) {
    for (var i = 0; i < pointToAdd.length - signal_strengths[0].length; i++) {
      for (var point = 0; point < signal_strengths.length; point++) {
        signal_strengths[point].push(null);
      }
    }
  }
  signal_strengths.push(pointToAdd);
  console.log(signal_strengths);
}

function getData() {
  $.getJSON('/content.json?checksum=42', function(data) {
    var d = new Date();
    var time = d.getTime() / 1000 - curTime / 1000; // so it's not really big
    addPoint(time, data['signal_strength']);
    if (!initialized) {
      initializeDygraph();
      initialized = true;
    }
    else {
      g.updateOptions({file: signal_strengths});
    }
  });
  setTimeout(function() {
    getData();
  }, 1000);
}
