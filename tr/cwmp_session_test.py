#!/usr/bin/python
#
# Copyright 2012 Google Inc. All Rights Reserved.
#
# unittest requires method names starting in 'test'
#pylint: disable-msg=C6409

"""Unit tests for cwmp_session.py"""

__author__ = 'dgentry@google.com (Denton Gentry)'

import fix_path

import sys
import cwmp_session
import unittest

class CwmpSessionTest(unittest.TestCase):
  """tests for cwmp_session.py."""
  def testStateStart(self):
    cs = cwmp_session.CwmpSession("")
    self.assertTrue(cs.inform_required())
    self.assertFalse(cs.request_allowed())
    self.assertFalse(cs.response_allowed())

    # should be no change
    cs.state_update(on_hold=True)
    self.assertTrue(cs.inform_required())
    self.assertFalse(cs.request_allowed())
    self.assertFalse(cs.response_allowed())

    cs.state_update(cpe_to_acs_empty=True)
    self.assertTrue(cs.inform_required())
    self.assertFalse(cs.request_allowed())
    self.assertFalse(cs.response_allowed())

    cs.state_update(acs_to_cpe_empty=True)
    self.assertTrue(cs.inform_required())
    self.assertFalse(cs.request_allowed())
    self.assertFalse(cs.response_allowed())

    # transition to ACTIVE
    cs.state_update(sent_inform=True)
    self.assertFalse(cs.inform_required())
    self.assertTrue(cs.request_allowed())
    self.assertTrue(cs.response_allowed())

  def testActive(self):
    cs = cwmp_session.CwmpSession("")
    cs.state_update(sent_inform=True)
    self.assertFalse(cs.inform_required())
    self.assertTrue(cs.request_allowed())
    self.assertTrue(cs.response_allowed())

    # should be no change
    cs.state_update(sent_inform=True)
    self.assertFalse(cs.inform_required())
    self.assertTrue(cs.request_allowed())
    self.assertTrue(cs.response_allowed())
    cs.state_update(acs_to_cpe_empty=True)
    self.assertFalse(cs.inform_required())
    self.assertTrue(cs.request_allowed())
    self.assertTrue(cs.response_allowed())

    # transition to ONHOLD
    cs.state_update(on_hold=True)
    self.assertFalse(cs.inform_required())
    self.assertFalse(cs.request_allowed())
    self.assertTrue(cs.response_allowed())

    # transition back to ACTIVE
    cs.state_update(on_hold=False)
    self.assertFalse(cs.inform_required())
    self.assertTrue(cs.request_allowed())
    self.assertTrue(cs.response_allowed())

    # transition to NOMORE
    cs.state_update(cpe_to_acs_empty=True)
    self.assertFalse(cs.inform_required())
    self.assertFalse(cs.request_allowed())
    self.assertTrue(cs.response_allowed())

  def testOnHold(self):
    cs = cwmp_session.CwmpSession("")
    cs.state_update(sent_inform=True)
    cs.state_update(on_hold=True)
    self.assertFalse(cs.inform_required())
    self.assertFalse(cs.request_allowed())
    self.assertTrue(cs.response_allowed())

    # No change
    cs.state_update(on_hold=True)
    self.assertFalse(cs.inform_required())
    self.assertFalse(cs.request_allowed())
    self.assertTrue(cs.response_allowed())

    cs.state_update(sent_inform=True)
    self.assertFalse(cs.inform_required())
    self.assertFalse(cs.request_allowed())
    self.assertTrue(cs.response_allowed())

    cs.state_update(cpe_to_acs_empty=True)
    self.assertFalse(cs.inform_required())
    self.assertFalse(cs.request_allowed())
    self.assertTrue(cs.response_allowed())

    cs.state_update(acs_to_cpe_empty=True)
    self.assertFalse(cs.inform_required())
    self.assertFalse(cs.request_allowed())
    self.assertTrue(cs.response_allowed())

    # back to ACTIVE
    cs.state_update(on_hold=False)
    self.assertFalse(cs.inform_required())
    self.assertTrue(cs.request_allowed())
    self.assertTrue(cs.response_allowed())

  def testNoMore(self):
    cs = cwmp_session.CwmpSession("")

    # transition to NOMORE
    cs.state_update(sent_inform=True)
    cs.state_update(cpe_to_acs_empty=True)
    self.assertFalse(cs.inform_required())
    self.assertFalse(cs.request_allowed())
    self.assertTrue(cs.response_allowed())

    # should be no change
    cs.state_update(sent_inform=True)
    self.assertFalse(cs.inform_required())
    self.assertFalse(cs.request_allowed())
    self.assertTrue(cs.response_allowed())

    cs.state_update(on_hold=True)
    self.assertFalse(cs.inform_required())
    self.assertFalse(cs.request_allowed())
    self.assertTrue(cs.response_allowed())

    # transition to DONE
    cs.state_update(acs_to_cpe_empty=True)
    self.assertFalse(cs.inform_required())
    self.assertFalse(cs.request_allowed())
    self.assertFalse(cs.response_allowed())

  def testDone(self):
    cs = cwmp_session.CwmpSession("")
    cs.state_update(sent_inform=True)
    cs.state_update(cpe_to_acs_empty=True)
    cs.state_update(acs_to_cpe_empty=True)
    self.assertFalse(cs.inform_required())
    self.assertFalse(cs.request_allowed())
    self.assertFalse(cs.response_allowed())

    cs.state_update(sent_inform=True)
    self.assertFalse(cs.inform_required())
    self.assertFalse(cs.request_allowed())
    self.assertFalse(cs.response_allowed())

    cs.state_update(cpe_to_acs_empty=True)
    self.assertFalse(cs.inform_required())
    self.assertFalse(cs.request_allowed())
    self.assertFalse(cs.response_allowed())

    cs.state_update(acs_to_cpe_empty=True)
    self.assertFalse(cs.inform_required())
    self.assertFalse(cs.request_allowed())
    self.assertFalse(cs.response_allowed())

    cs.state_update(sent_inform=True)
    self.assertFalse(cs.inform_required())
    self.assertFalse(cs.request_allowed())
    self.assertFalse(cs.response_allowed())


if __name__ == '__main__':
  unittest.main()
