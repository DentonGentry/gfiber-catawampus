wvtest('tests indexes of added devices', function() {
  var list = new deviceList();
  WVPASSEQ(list.get('01:02:03:04:05:06') , 0);
  WVPASSEQ(list.get('01:02:03:04:05:06') , 0);
  WVPASSEQ(list.get('01:02:03:04:05:07') , 1);
  WVPASSEQ(list.get('01:02:03:04:05:06') , 0);
  var data = {};
  hostHelper(list.hostNames(data), {'01:02:03:04:05:06': '01:02:03:04:05:06',
    '01:02:03:04:05:07': '01:02:03:04:05:07'});
  data['01:02:03:04:05:06'] = 'iPhone';
  hostHelper(list.hostNames(data, false) , {'01:02:03:04:05:06': 'iPhone',
    '01:02:03:04:05:07': '01:02:03:04:05:07'});
  data['01:02:03:04:05:07'] = '';
  hostHelper(list.hostNames(data, false) , {'01:02:03:04:05:06': 'iPhone',
  '01:02:03:04:05:07': '01:02:03:04:05:07'});
  data = {'01:02:03:04:05:06': 'iPhone'};
  hostHelper(list.hostNames(data, false) , {'01:02:03:04:05:06': 'iPhone',
  '01:02:03:04:05:07': '01:02:03:04:05:07'});
});

function hostHelper(obj1, obj2) {
  for (var key in obj1) {
    WVPASSEQ(obj1[key], obj2[key]);
  }
  for (var key in obj2) {
    WVPASSEQ(obj1[key], obj2[key]);
  }
}
