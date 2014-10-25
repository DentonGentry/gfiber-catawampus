DiagUI = function() {
  // Do some feature sniffing for dependencies and return if not supported.
  if (!window.XMLHttpRequest ||
      !document.querySelector ||
      !Element.prototype.addEventListener ||
      !('classList' in document.createElement('_'))) {
    document.documentElement.classList.add('unsupported');
    return;
  }

  // Add click event listeners.
  document.querySelector('#advanced button.toggle').addEventListener(
      'click', DiagUI.toggleAdvanced);
  document.querySelector('#restart .button.restart').addEventListener(
      'click', DiagUI.openRestartDialog);
  document.querySelector('#dialog .button.restart').addEventListener(
      'click', DiagUI.tryRestart);
  document.querySelector('#dialog .button.cancel').addEventListener(
      'click', DiagUI.closeRestartDialog);
  document.querySelector('#save .button').addEventListener(
      'click', DiagUI.saveDiagInfo);

  // Initialize the diagnostic info.
  DiagUI.getDiagInfo();

  // Refresh data periodically.
  window.setInterval(DiagUI.getDiagInfo, 30000);
};


DiagUI.info = {checksum: 0};


DiagUI.toggleAdvanced = function() {
  // Toggle the collapsed class on the advanced element.
  document.getElementById('advanced').classList.toggle('collapsed');
};


DiagUI.openRestartDialog = function(e) {
  // Prevent the form from submitting by default.
  e.preventDefault();
  // Add the dialog class to the html element and focus the restart button.
  document.documentElement.classList.add('dialog');
  document.querySelector('#dialog button.restart').focus();
};


DiagUI.closeRestartDialog = function() {
  // Remove the dialog class from the html element and focus the restart button.
  document.documentElement.classList.remove('dialog');
  document.querySelector('#restart .button.restart').focus();
};


DiagUI.setConnectedStatus = function(connected) {
  // Remove the init class to update styles.
  document.documentElement.classList.remove('init');

  // Toggle the dis/connected classes on the html element and set the status.
  if (connected) {
    document.documentElement.classList.add('connected');
    document.documentElement.classList.remove('disconnected');
    document.getElementById('status').innerText =
        document.getElementById('status').getAttribute('data-connected');
  } else {
    document.documentElement.classList.add('disconnected');
    document.documentElement.classList.remove('connected');
    document.getElementById('status').innerText =
        document.getElementById('status').getAttribute('data-disconnected');
  }
};


DiagUI.updateField = function(key, val) {
  var el = document.getElementById(key);
  el.innerHTML = ''; // Clear the field.
  // For objects, create an unordered list and append the values as list items.
  if (val && typeof val === 'object') {
    var ul = document.createElement('ul');
    for (key in val) {
      var li = document.createElement('li');
      var primary = document.createTextNode(key + ' ');
      li.appendChild(primary);
      var secondary = document.createElement('span');
      secondary.textContent = val[key];
      li.appendChild(secondary);
      ul.appendChild(li);
    }
    // If the unordered list has children, append it and return.
    if (ul.hasChildNodes()) {
      el.appendChild(ul);
      return;
    } else {
      val = 'N/A';
    }
  }
  if (!val) {
    val = 'N/A';
  }
  el.appendChild(document.createTextNode(val));
};


DiagUI.getDiagInfo = function() {
  // Request diagnostic info, set the connected status, and update the fields.
  var xhr = new XMLHttpRequest();
  xhr.onreadystatechange = function() {
    if (xhr.readyState == 4 && xhr.status == 200) {
      DiagUI.info = JSON.parse(xhr.responseText);
      DiagUI.setConnectedStatus(DiagUI.info.connected);
      DiagUI.updateField('ssid', DiagUI.info.ssid24 || 'Network Box');
      DiagUI.updateField('acs', DiagUI.info.acs);
      DiagUI.updateField('softversion', DiagUI.info.softversion);
      DiagUI.updateField('uptime', DiagUI.info.uptime);
      DiagUI.updateField('temperature', DiagUI.info.temperature);
      DiagUI.updateField('wanmac', DiagUI.info.wanmac);
      DiagUI.updateField('wanip', DiagUI.info.wanip);
      DiagUI.updateField('lanip', DiagUI.info.lanip);
      DiagUI.updateField('subnetmask', DiagUI.info.subnetmask);
      DiagUI.updateField('lanmac', DiagUI.info.lanmac);
      DiagUI.updateField('wireddevices', DiagUI.info.wireddevices);
      DiagUI.updateField('ssid24', DiagUI.info.ssid24);
      DiagUI.updateField('ssid5', DiagUI.info.ssid5);
      DiagUI.updateField('wpa2', DiagUI.info.wpa2);
      DiagUI.updateField('wirelesslan', DiagUI.info.wirelesslan);
      DiagUI.updateField('wirelessdevices', DiagUI.info.wirelessdevices);
      DiagUI.updateField('upnp', DiagUI.info.upnp);
      DiagUI.updateField('username', DiagUI.info.username);
      DiagUI.updateField('onu_serial', DiagUI.info.onu_serial);
      DiagUI.updateField('onu_wan_connected', DiagUI.info.onu_wan_connected);
      DiagUI.updateField('onu_acs_contacted', DiagUI.info.onu_acs_contacted);
      var onu_acs_contact_time;
      if ('onu_acs_contact_time' in DiagUI.info) {
        onu_acs_contact_time =
            String(new Date(DiagUI.info.onu_acs_contact_time * 1000));
      }
      DiagUI.updateField('onu_acs_contact_time', onu_acs_contact_time);
      DiagUI.updateField('onu_uptime', DiagUI.info.onu_uptime);
    }
  };
  var payload = [];
  payload.push('checksum=' + encodeURIComponent(DiagUI.info.checksum));
  payload.push('_=' + encodeURIComponent((new Date()).getTime()));
  xhr.open('get', 'content.json?' + payload.join('&'), true);
  xhr.send();
};


DiagUI.saveDiagInfo = function(e) {
  var URL = window.URL || window.webkitURL;
  var table = document.querySelector('#advanced table');
  // For browsers that don't support blobs and file, open a new window instead.
  if (!window.Blob || !URL.createObjectURL) {
    e.preventDefault();
    var newWin = window.open('', '');
    newWin.document.body.appendChild(table.cloneNode(true));
    newWin.document.close();
    newWin.focus();
  }
  // Revoke the last URL to clear from memory.
  if (this.href) {
    URL.revokeObjectURL(this.href);
  }
  // Create the text file, generate a filename, and update the download link.
  var blob = new Blob([table.innerText || table.textContent], {
    type: 'text/plain;charset=utf-8'
  });
  var now = new Date();
  var filename = DiagUI.info.ssid24 || 'Network Box';
  filename += ' ';
  filename += now.getFullYear();
  filename += ('0' + (now.getMonth() + 1)).slice(-2);
  filename += ('0' + now.getDate()).slice(-2);
  filename += ' diagnostic.txt';
  this.download = filename;
  this.href = URL.createObjectURL(blob);
};

DiagUI.tryRestart = function(e) {
  // Prevent the form from submitting by default.
  e.preventDefault();

  // Remove the dialog class from the html element and add the loading class.
  document.documentElement.classList.remove('dialog');
  document.documentElement.classList.add('loading');

  // Repeatedly request the restart page until it loads successfully within 1s.
  var timeoutFirstMs = 15000;
  var timeoutAfterMs = 8000;
  var intervalMs = 1000;
  var startReboot = false;
  window.setInterval(function() {
    var xhr = new XMLHttpRequest();
    var token = document.querySelector('input[name="_xsrf"]').value;
    xhr.timeout = timeoutFirstMs;
    xhr.onreadystatechange = function() {
      if (xhr.status != 200) {
        startReboot = true;
      } else if (xhr.readyState == 4) {
        if (startReboot) {
          window.location.assign('/');
        }
      }
    };
    xhr.open('post', '/restart', true);
    xhr.setRequestHeader("X-CSRFToken", token);
    xhr.send();
  }, intervalMs);

  // Set a timeout to remove the loading class from the html element and add the
  // error class.
  window.setTimeout(function() {
    document.documentElement.classList.remove('loading');
    document.documentElement.classList.add('error');
    timeoutFirstMs = timeoutAfterMs;
  }, 60000);
};

new DiagUI();
