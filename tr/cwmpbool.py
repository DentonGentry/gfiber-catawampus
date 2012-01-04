# Copyright 2011 Google Inc. All Rights Reserved.

"""Boolean handling for CWMP.

TR-069 Amendment 3, Annex A says:
Boolean, where the allowed values are "0", "1", "true", and "false".
The values "1" and "true" are considered interchangeable, where both
equivalently represent the logical value true. Similarly, the values
"0" and "false" are considered interchangeable, where both equivalently
represent the logical value false.
"""

__author__ = 'dgentry@google.com (Denny Gentry)'

def format(arg):
  """Print a CWMP boolean object."""
  return "1" if arg else "0"

def parse(arg):
  lower = arg.lower()
  if lower == "false" or lower == "0":
    return False
  else:
    return True
