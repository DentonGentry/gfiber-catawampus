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

  @abc.abstractmethod
  def GetAcsUrl(self):
    """Return the current ACS_URL.

    Handling of the ACS URL to use is platform and/or deployment specific.
    For example, the platform may implement the CWMP ACS_URL option for DHCP,
    or it may have a hard-coded ACS URL for a particular ISP deployment.
    """
    return None

  @abc.abstractmethod
  def SetAcsUrl(self, url):
    """Called for a SetParameterValue of DeviceInfo.ManagementServer.URL.

    Args:
      url: the URL to set

    It is up to the platform to determine the relative priority of ACS URLs
    set via DeviceInfo.ManagementServer.URL versus other mechanisms.

    If the platform does not allow the ACS to be set, this routine should
    raise an AttributeError.
    """
    return None

  @abc.abstractmethod
  def InvalidateAcsUrl(self, url):
    """Removes the given URL from the set of ACS urls to choose from.

    Args:
      url: The URL to invalidate.

    A URL may be found to be invalid if it doesn't match the restrict list.
    For example, if the restrict list is set to '.foo.com' and the url
    returned from GetAcsUrl is 'xxx.bar.com', the then InvalidateAcsUrl will
    be called, and the platform code has a chance to return a different URL.
    This can happen if for example the DHCP server is misconfigured, and
    points to a server/domain that is not on the restrict list, and give the
    platform code a chance to return a default URL, or a URL gotten by some
    other means.

    Returns: True on success.  False if there was an error invalidating.
    """
    return True

  @abc.abstractmethod
  def AcsAccessAttempt(self, url):
    """Called before attempting to initiate a connection with the ACS.

    Args:
      url: the ACS_URL being contacted.
    """
    return None

  @abc.abstractmethod
  def AcsAccessSuccess(self, url):
    """Called at the end of every successful ACS session.

    Args:
      url: the ACS_URL being contacted.
    """
    return None
