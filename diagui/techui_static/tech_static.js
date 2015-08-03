var wifi = new SignalStrengthChart('Signal Strength (dBm)', 'RSSI',
                                   'wifi_signal_strength', 'wifi_graph',
                                   'rssi_labels', false);
var moca = new SignalStrengthChart('Signal Strength (dB)', 'MOCA Signal',
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

var graph_array = [wifi, moca, corrected_cwrds, uncorrected_cwrds, aps, me_ap];

$(document).ready(function() {getData(graph_array);});
