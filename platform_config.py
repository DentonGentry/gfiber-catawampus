#!/usr/bin/python
# Copyright 2012 Google Inc. All Rights Reserved.
#
"""Platform-specific information which the rest of Catawampus needs."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import abc


class PlatformConfigMeta(object):
  """Class to provide platform-specific information like directory locations.

  Each platform is expected to subclass PlatformMeta and supply concrete
  implementations of all methods. We use a Python Abstract Base Class
  to protect against future versions. If we add fields to this class,
  any existing platform implementations will be prompted to add implementations
  (because they will fail to startup when their PlatformMeta fails to
  instantiate).
  """
  __metaclass__ = abc.ABCMeta

  @abc.abstractmethod
  def ConfigDir(self):
    """Directory where configs and download metadata should be stored.

    This directory needs to persist its contents across reboots. It will
    store configs of a few tens to hundreds of kilobytes, and metadata about
    a small number of active downloads of less than one Kbyte each.
    """
    return None

  @abc.abstractmethod
  def DownloadDir(self):
    """Directory where downloaded files should be stored.

    This directory will store software image downloads, which can be large
    but do not need to survive a reboot. An image is downloaded and applied,
    then the system reboots.
    """
    return None
