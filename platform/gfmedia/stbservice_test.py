#!/usr/bin/python
#
# Copyright 2012 Google Inc. All Rights Reserved.
#
# unittest requires method names starting in 'test'
#pylint: disable-msg=C6409

"""Unit tests for stbservice.py implementation."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import unittest

import google3
import stbservice


class STBServiceTest(unittest.TestCase):
  def setUp(self):
    self.old_PROCNETIGMP = stbservice.PROCNETIGMP
    stbservice.PROCNETIGMP = 'testdata/stbservice/igmp'

  def tearDown(self):
    stbservice.PROCNETIGMP = self.old_PROCNETIGMP

  def testValidateExports(self):
    stb = stbservice.STBService()
    stb.ValidateExports()

  def testClientGroups(self):
    stb = stbservice.STBService()
    self.assertEqual(
        len(stb.Components.FrontEndList['1'].IP.IGMP.ClientGroupList), 2)
    expected = set(['224.0.0.1', '224.0.0.251'])
    expected.remove(
        stb.Components.FrontEndList['1'].IP.IGMP.ClientGroupList['1'].GroupAddress)
    expected.remove(
        stb.Components.FrontEndList['1'].IP.IGMP.ClientGroupList['2'].GroupAddress)
    self.assertEqual(len(expected), 0)


if __name__ == '__main__':
  unittest.main()
