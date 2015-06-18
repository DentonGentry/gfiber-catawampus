wvtest('tests indexes of added devices', function() {
  var list = new deviceList();
  WVPASSEQ(list.get('01:02:03:04:05:06') , 0);
  WVPASSEQ(list.get('01:02:03:04:05:06') , 0);
  WVPASSEQ(list.get('01:02:03:04:05:07') , 1);
  WVPASSEQ(list.get('01:02:03:04:05:06') , 0);
  var array = [];
  WVPASSEQ(list.hostNames(array) , ['01:02:03:04:05:06', '01:02:03:04:05:07']);
  array['01:02:03:04:05:06'] = 'iPhone';
  WVPASSEQ(list.hostNames(array) , ['iPhone', '01:02:03:04:05:07']);
  array['01:02:03:04:05:07'] = '';
  WVPASSEQ(list.hostNames(array) , ['iPhone', '01:02:03:04:05:07']);
});
