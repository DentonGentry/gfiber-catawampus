var console = {};

/** So we can use wvtest
 * @param {string} string - takes in a string to print it
*/
console.log = function(string) {
   print(string);
};

wvtest('test adding points', function() {
  //console.log(signal_strengths);
  addPoint(1, {'mac1': 1});
  //console.log(signal_strengths);
  WVPASSEQ(signal_strengths.length, 1);
  WVPASSEQ(signal_strengths[0].length, 2);
  WVPASSEQ(signal_strengths[0][1] , 1);

  addPoint(2, {'mac1': 2});
  WVPASSEQ(signal_strengths.length, 2);
  WVPASSEQ(signal_strengths[1].length, 2);
  WVPASSEQ(signal_strengths[1][1] , 2);

  addPoint(3, {'mac2': 3});
  WVPASSEQ(signal_strengths.length, 3);
  WVPASSEQ(signal_strengths[2].length, 3);
  WVPASSEQ(signal_strengths[2][1] , undefined);
  WVPASSEQ(signal_strengths[2][2] , 3);

  //undefined was populated into the previous array elements
  console.log(signal_strengths[0].length);
  WVPASSEQ(signal_strengths[0].length, 3);
  WVPASSEQ(signal_strengths[1].length, 3);
  WVPASSEQ(signal_strengths[0][2] , null);
  WVPASSEQ(signal_strengths[1][2] , undefined);
});
