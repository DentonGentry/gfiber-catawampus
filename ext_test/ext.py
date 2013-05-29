"""Test for extension modules in the top of $CWMPD_EXT_DIR."""


def Extend(root):
  root.TestBaseExt = True
  root.Export(params=['TestBaseExt'])
