var deviceList = function() {
  this.devices = {};
  this.next = 0;
  this.host_names = {};
};

/** Takes a mac addr and returns the index.
 * @param {string} mac_addr - MAC address to index
 * @return {int} returns index of specified MAC address
*/
deviceList.prototype.get = function(mac_addr) {
  if (mac_addr in this.devices) {
       return this.devices[mac_addr];
   }
   this.devices[mac_addr] = this.next++;
   return this.devices[mac_addr];
};

/** Takes an array of host names and returns the ones in
 *  the device list.
 * @param {array} host_data - host names data (could have empty fields)
 * @return {array} returns array of device host names
*/
deviceList.prototype.hostNames = function(host_data) {
  for (var mac_addr in this.devices) {
    if (host_data[mac_addr] == '' ||
    typeof host_data[mac_addr] == 'undefined') {
      this.host_names[mac_addr] = mac_addr;
    } else {
      this.host_names[mac_addr] = host_data[mac_addr];
    }
  }
  return this.host_names;
}
