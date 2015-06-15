var deviceList = function() {
  this.devices = {};
  this.next = 0;
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
  var host_names = [];
  for (var mac_addr in this.devices) {
     host_names.push(host_data[mac_addr]);
  }
  return host_names;
}
