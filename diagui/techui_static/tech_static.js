var wifi = new SignalStrengthChart('Signal Strength (dBm)', 'RSSI',
                                   'wifi_signal_strength', 'wifi_graph',
                                   'rssi_labels');
var moca = new SignalStrengthChart('Signal Strength (dB)', 'MOCA',
                                   'moca_signal_strength', 'moca_graph',
                                   'moca_labels');
var corrected_cwrds = new SignalStrengthChart('Erroneous Codewords to Total',
                                             'Corrected Codewords',
                                             'moca_corrected_codewords',
                                             'corrected_codewords',
                                             'cor_cw_labels');
var uncorrected_cwrds = new SignalStrengthChart('Erroneous Codewords to Total',
                                                'Uncorrected Codewords',
                                                'moca_uncorrected_codewords',
                                                'uncorrected_codewords',
                                                'uncor_cw_labels');
var aps = new SignalStrengthChart('Signal Strength (dBm)', 'Other APs',
                                  'other_aps', 'aps_graph',
                                  'ap_labels');
var me_ap = new SignalStrengthChart('Signal Strength (dBm)',
                                    'Me as seen by other APs',
                                    'self_signals', 'me_ap_graph',
                                    'me_ap_labels');
$(document).ready(function() {wifi.getData(false);
                              moca.getData(true);
                              aps.getData(false);
                              me_ap.getData(false);
                              corrected_cwrds.getData(true);
                              uncorrected_cwrds.getData(true);});
