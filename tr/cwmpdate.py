# Copyright 2011 Google Inc. All Rights Reserved.

"""Time handling for CWMP.

CWMP uses ISO 8601 time strings, and further specifies that UTC time be
used unless otherwise specified (and then, to my knowledge, never
specifies a case where another timezone can be used).

Python datetime objects are suitable for use with CWMP so long as
they contain a tzinfo specifying UTC offset=0. Most Python programmers
create datetime objects with no tzinfo, so we add one.
"""

__author__ = 'dgentry@google.com (Denny Gentry)'

import datetime

def cwmpformat(dt):
  """Print a datetime object with 'Z' for the UTC timezone, as CWMP requires."""
  if not dt:
    return "0001-01-01T00:00:00Z"  # CWMP Unknown Time
  elif not dt.tzinfo or not dt.tzinfo.utcoffset(dt):
    if dt.microsecond:
      return dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    else:
      return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
  else:
    return dt.isoformat()
