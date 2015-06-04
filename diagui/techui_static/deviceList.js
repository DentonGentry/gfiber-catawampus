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
}
