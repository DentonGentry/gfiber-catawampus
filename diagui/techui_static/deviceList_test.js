wvtest('tests indexes of added devices', function() {
  var list = new deviceList();
  WVPASSEQ(list.get('01:02:03:04:05:06') , 0);
  WVPASSEQ(list.get('01:02:03:04:05:06') , 0);
  WVPASSEQ(list.get('01:02:03:04:05:07') , 1);
  WVPASSEQ(list.get('01:02:03:04:05:06') , 0);
});
