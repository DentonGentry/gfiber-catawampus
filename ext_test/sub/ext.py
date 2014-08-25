"""Test for extension modules in a subdir of $CWMPD_EXT_DIR."""

import google3
import tr.cwmptypes


def Extend(root):
  type(root).TestSubExt = tr.cwmptypes.Unsigned(42)
  root.TestSubExt = 97.3
  root.Export(params=['TestSubExt'])
