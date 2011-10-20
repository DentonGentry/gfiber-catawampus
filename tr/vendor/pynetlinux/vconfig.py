import fcntl
import os
import socket
import struct
import ctypes
import ifconfig

"""
This file makes the following assumptions about data structures:

// From linux/if_vlan.h
enum vlan_ioctl_cmds {
  ADD_VLAN_CMD,
  DEL_VLAN_CMD,
  SET_VLAN_INGRESS_PRIORITY_CMD,
  SET_VLAN_EGRESS_PRIORITY_CMD,
  GET_VLAN_INGRESS_PRIORITY_CMD,
  GET_VLAN_EGRESS_PRIORITY_CMD,
  SET_VLAN_NAME_TYPE_CMD,
  SET_VLAN_FLAG_CMD,
  GET_VLAN_REALDEV_NAME_CMD,
  GET_VLAN_VID_CMD
};

enum vlan_flags {
  VLAN_FLAG_REORDER_HDR = 0x1,
  VLAN_FLAG_GVRP = 0x2,
};

enum vlan_name_types {
  VLAN_NAME_TYPE_PLUS_VID, /* Name will look like:  vlan0005 */
  VLAN_NAME_TYPE_RAW_PLUS_VID, /* name will look like:  eth1.0005 */
  VLAN_NAME_TYPE_PLUS_VID_NO_PAD, /* Name will look like:  vlan5 */
  VLAN_NAME_TYPE_RAW_PLUS_VID_NO_PAD, /* Name will look like:  eth0.5 */
  VLAN_NAME_TYPE_HIGHEST
};

struct vlan_ioctl_args {
  int cmd; /* Should be one of the vlan_ioctl_cmds enum above. */
  char device1[24];

  union {
    char device2[24];
    int VID;
    unsigned int skb_priority;
    unsigned int name_type;
    unsigned int bind_type;
    unsigned int flag; /* Matches vlan_dev_info flags */
  } u;

  short vlan_qos;
};
"""

# From linux/sockios.h
SIOCGIFVLAN = 0x8982
SIOCSIFVLAN = 0x8983

# From linux/if_vlan.h
ADD_VLAN_CMD = 0
DEL_VLAN_CMD = 1
SET_VLAN_INGRESS_PRIORITY_CMD = 2
SET_VLAN_EGRESS_PRIORITY_CMD = 3
GET_VLAN_INGRESS_PRIORITY_CMD = 4
GET_VLAN_EGRESS_PRIORITY_CMD = 5
SET_VLAN_NAME_TYPE_CMD = 6
SET_VLAN_FLAG_CMD = 7
GET_VLAN_REALDEV_NAME_CMD = 8
GET_VLAN_VID_CMD = 9


class Vlan(object):
    ''' Class representing a Linux vlan. '''

    def __init__(self, name):
        self.name = name


    def get_realdev_name(self):
        '''Get the underlying netdev for a VLAN interface.'''
        vlanioc = struct.pack('i24s24sh', GET_VLAN_REALDEV_NAME_CMD,
                              self.name, '', 0)
        result = struct.unpack('i24s24sh',
                               fcntl.ioctl(ifconfig.sockfd, SIOCGIFVLAN, vlanioc))
        return result[2].rstrip('\0')


def shutdown():
    ''' Shut down the library '''
    ifconfig.shutdown()
