#!/usr/bin/python
#
# Copyright 2011 Google Inc. All Rights Reserved.

"""Unit tests for DeviceModel code generator.
"""

__author__ = 'dgentry@google.com (Denton Gentry)'

import cwmp_datamodel_1_3 as dm
import dm_codegen
import sys
import unittest

dm1_xml = """<dm:document xmlns:dm="urn:broadband-forum-org:cwmp:datamodel-1-2"
    xmlns:dmr="urn:broadband-forum-org:cwmp:datamodel-report-0-1"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="urn:broadband-forum-org:cwmp:datamodel-1-2 cwmp-datamodel-1-2.xsd 
                        urn:broadband-forum-org:cwmp:datamodel-report-0-1 cwmp-datamodel-report.xsd"
    spec="urn:broadband-forum-org:tr-181-2-0-1">
  <model name="DMTestModel">
    <description>A description</description>
    <object name="foo." access="readOnly" minEntries="1" maxEntries="1">
      <description>This is the foo object.</description>
      <parameter name="bar" access="readOnly">
        <description>This is the bar parameter</description>
        <syntax>
          <string>
            <size maxLength="12"/>
          </string>
        </syntax>
      </parameter>
    </object>
  </model>
</dm:document>"""

class DeviceModelCodegenTest(unittest.TestCase):
  def setUp(self):
    # for xmlwitch
    sys.path.append('..')

  def DoCodegen(self, xml):
    objdict = dict()
    root = dm.parseString(xml)
    dm_codegen.CollectObjects(objdict, root, [])
    out = []
    dm_codegen.EmitPrologue(out)
    for key, obj in sorted(objdict.items()):
      dm_codegen.EmitClassForObj(key, obj, out)
    return "".join(out)

  def testSimpleCodegen(self):
    pystr = self.DoCodegen(dm1_xml)
    self.assertTrue(len(pystr))
    try:
      exec(pystr)
      foo_obj = foo_()
    except (NameError, SyntaxError) as e:
      print(e)
      print("In generated code:")
      print(pystr)
      self.assertFalse(True)
    self.assertTrue(hasattr(foo_obj, 'p_bar'))
    self.assertFalse(hasattr(foo_obj, 'p_baz'))


if __name__ == '__main__':
  unittest.main()
