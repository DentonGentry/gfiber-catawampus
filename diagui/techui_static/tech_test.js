var console = {};

/** So we can use wvtest
 * @param {string} string - takes in a string to print it
*/
console.log = function(string) {
   print(string);
};

wvtest('test adding points', function() {
  //console.log(chart.signalStrengths);
  var chart = new SignalStrengthChart();
  chart.addPoint(1, {'mac1': 1});
  //console.log(chart.signalStrengths);
  WVPASSEQ(chart.signalStrengths.length, 1);
  WVPASSEQ(chart.signalStrengths[0].length, 2);
  WVPASSEQ(chart.signalStrengths[0][1] , 1);

  chart.addPoint(2, {'mac1': 2});
  WVPASSEQ(chart.signalStrengths.length, 2);
  WVPASSEQ(chart.signalStrengths[1].length, 2);
  WVPASSEQ(chart.signalStrengths[1][1] , 2);

  chart.addPoint(3, {'mac2': 3});
  WVPASSEQ(chart.signalStrengths.length, 3);
  WVPASSEQ(chart.signalStrengths[2].length, 3);
  WVPASSEQ(chart.signalStrengths[2][1] , undefined);
  WVPASSEQ(chart.signalStrengths[2][2] , 3);

  //undefined was populated into the previous array elements
  console.log(chart.signalStrengths[0].length);
  WVPASSEQ(chart.signalStrengths[0].length, 3);
  WVPASSEQ(chart.signalStrengths[1].length, 3);
  WVPASSEQ(chart.signalStrengths[0][2] , null);
  WVPASSEQ(chart.signalStrengths[1][2] , undefined);
});
