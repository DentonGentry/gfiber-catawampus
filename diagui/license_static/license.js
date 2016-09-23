$('document').ready(function() {
  // Normal Ajax request tries to decode binary content as text and
  // corrupts zip file. We use JSZipUtils function which handles this
  JSZipUtils.getBinaryContent('/license/LICENSES.zip?', function(err, data) {
    if (err) {
      console.log('ERROR');
      console.log(err);
      return;
    }

    JSZip.loadAsync(data)
        .then(function(zip) {
          return zip.file('LICENSES').async('string');
        }).then(function(text) {
          $('#license-text').html(text);
        });
  });
});
