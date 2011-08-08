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
      <parameter name="bar_boolean" access="readOnly">
        <description>This is the bar boolean parameter</description>
        <syntax>
          <boolean/>
          <default type="object" value="True"/>
        </syntax>
      </parameter>
      <parameter name="bar_string" access="readOnly">
        <description>This is the bar unsignedInt parameter</description>
        <syntax>
          <string/>
          <default type="object" value="BarDefault"/>
        </syntax>
      </parameter>
      <parameter name="bar_unsignedint" access="readOnly">
        <description>This is the bar unsignedInt parameter</description>
        <syntax>
          <unsignedInt/>
          <default type="object" value="12"/>
        </syntax>
      </parameter>
      <parameter name="bar_unsignedlong" access="readOnly">
        <description>This is the bar unsignedLong parameter</description>
        <syntax>
          <unsignedLong/>
          <default type="object" value="27"/>
        </syntax>
      </parameter>
      <parameter name="bar_int" access="readOnly">
        <description>This is the bar int parameter</description>
        <syntax>
          <int/>
          <default type="object" value="31"/>
        </syntax>
      </parameter>
      <parameter name="bar_long" access="readOnly">
        <description>This is the bar long parameter</description>
        <syntax>
          <long/>
          <default type="object" value="56"/>
        </syntax>
      </parameter>
    </object>
  </model>
</dm:document>"""

dm1_out = """<object name=\"foo\">
  <bar_boolean>True</bar_boolean>
  <bar_string>BAR_STRING</bar_string>
  <bar_unsignedint>256</bar_unsignedint>
  <bar_unsignedlong>128</bar_unsignedlong>
  <bar_int>64</bar_int>
  <bar_long>32</bar_long>
</object>"""

class DeviceModelCodegenTest(unittest.TestCase):
  def setUp(self):
    sys.path.append('..')  # for xmlwitch
    import xmlwitch
    pystr = self.DoCodegen(dm1_xml)
    self.assertTrue(len(pystr))
    try:
      exec(pystr, globals(), globals())
    except:
      print("In generated code:")
      print(pystr)
      raise

  def DoCodegen(self, xml):
    objdict = dict()
    root = dm.parseString(xml)
    dm_codegen.CollectObjects(objdict, root, [])
    out = []
    dm_codegen.EmitPrologue(out)
    for key, obj in sorted(objdict.items()):
      dm_codegen.EmitClassForObj(key, obj, out)
    return "".join(out)

  def MakeFoo(self):
    try:
      foo_obj = foo_()
    except SyntaxError as e:
      print(e)
      foo_obj = None
    self.assertTrue(foo_obj)
    return foo_obj

  def testCodegenProperties(self):
    foo_obj = self.MakeFoo()
    self.assertTrue(hasattr(foo_obj, 'p_bar_boolean'))
    self.assertTrue(hasattr(foo_obj, 'p_bar_string'))
    self.assertTrue(hasattr(foo_obj, 'p_bar_unsignedint'))
    self.assertTrue(hasattr(foo_obj, 'p_bar_unsignedlong'))
    self.assertTrue(hasattr(foo_obj, 'p_bar_int'))
    self.assertTrue(hasattr(foo_obj, 'p_bar_long'))
    self.assertFalse(hasattr(foo_obj, 'p_baz_string'))
    self.assertFalse(hasattr(foo_obj, 'bar_string'))

  def testDefaultValues(self):
    foo_obj = self.MakeFoo()
    # values declared using <default> nodes in dm1_xml
    self.assertEqual(foo_obj.p_bar_boolean, True)
    self.assertEqual(foo_obj.p_bar_string, "BarDefault")
    self.assertEqual(foo_obj.p_bar_unsignedint, int(12))
    self.assertEqual(foo_obj.p_bar_unsignedlong, int(27))
    self.assertEqual(foo_obj.p_bar_int, int(31))
    self.assertEqual(foo_obj.p_bar_long, int(56))

  def testSerializeXml(self):
    foo_obj = self.MakeFoo()
    foo_obj.bar_boolean = True
    foo_obj.bar_string = "BAR_STRING"
    foo_obj.bar_unsignedint = 256
    foo_obj.bar_unsignedlong = 128
    foo_obj.bar_int = 64
    foo_obj.bar_long = 32
    xml = xmlwitch.Builder(encoding='utf-8')
    self.assertEqual(foo_obj.ToXml(xml), dm1_out)


if __name__ == '__main__':
  unittest.main()
