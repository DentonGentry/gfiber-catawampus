var wifi = new SignalStrengthChart('RSSI (dBm)', 'Signal Strength',
                                   'wifi_signal_strength', 'wifi_graph',
                                   'rssi_labels', false);
var wifiblaster = new SignalStrengthChart('Mbps', 'Estimated Throughput',
                                   'wifiblaster_results', 'wifiblaster_graph',
                                   'wifiblaster_labels', false);
var moca = new SignalStrengthChart('Signal-to-noise Ratio (dB)', 'MOCA SNR',
                                   'moca_signal_strength', 'moca_graph',
                                   'moca_labels', true);
var corrected_cwrds = new SignalStrengthChart('Erroneous Codewords to Total',
                                             'Corrected Codewords',
                                             'moca_corrected_codewords',
                                             'corrected_codewords',
                                             'cor_cw_labels', true);
var uncorrected_cwrds = new SignalStrengthChart('Erroneous Codewords to Total',
                                                'Uncorrected Codewords',
                                                'moca_uncorrected_codewords',
                                                'uncorrected_codewords',
                                                'uncor_cw_labels', true);
var aps = new SignalStrengthChart('Signal Strength (dBm)', 'Other APs',
                                  'other_aps', 'aps_graph',
                                  'ap_labels', false);
var me_ap = new SignalStrengthChart('Signal Strength (dBm)',
                                    'Me as seen by other APs',
                                    'self_signals', 'me_ap_graph',
                                    'me_ap_labels', false);

/* Isostream graphs */
var offset = new SignalStrengthChart('Offset (seconds)',
                                     'Isostream Offset',
                                     'isostream_last_log', 'isos_offset',
                                     'offset_labels', false);
var disconn = new SignalStrengthChart('Disconnects',
                                      'Isostream Disconnects',
                                      'isostream_last_log', 'isos_disconn',
                                      'disconn_labels', false);
var drops = new SignalStrengthChart('Drops',
                                    'Isostream Drops',
                                    'isostream_last_log', 'isos_drops',
                                    'drops_labels', false);

var graph_array = [wifi, moca];

$(document).ready(function() {
  getData(graph_array);
});

$('#isostream_button').click(function(e) {
  e.preventDefault();
  $('#isos_status').html('');
  var token = document.querySelector('input[name="_xsrf"]').value;
  $.ajax({
    type: 'POST',
    url: '/startisostream',
    beforeSend: function(request) {
      request.setRequestHeader('X-CSRFToken', token);
    },
    success: function(data) {
      $('#isos_status').html('');
      for (var ipAddr in data) {
        var text = $('<span></span>').text(
          'Starting isostream client on ' +
          ipAddr + ': ' + data[ipAddr]);
        $('#isos_status').append(text);
        $('#isos_status').append('<br>');
      }
      getIsostreamData(false);
    }
  });
});
