#!/usr/bin/python
#
# Copyright 2011 Google Inc. All Rights Reserved.
#
# unittest requires method names starting in 'test'
#pylint: disable-msg=C6409

"""Unit tests for cwmpd."""

__author__ = 'apenwarr@google.com (Avery Pennarun)'

import os
import subprocess
import unittest
import google3


class RunserverTest(unittest.TestCase):
  """Tests for cwmpd and cwmp."""

  def _DoTest(self, args):
    print
    print 'Testing with args=%r' % args
    sockname = '/tmp/cwmpd_test.sock.%d' % os.getpid()
    if os.path.exists(sockname):
      os.unlink(sockname)
    server = subprocess.Popen(['./cwmpd',
                               '--rcmd-port', '0',
                               '--unix-path', sockname,
                               '--close-stdio'] + args,
                              stdout=subprocess.PIPE, stdin=subprocess.PIPE)
    try:
      print 'waiting for server to start...'
      while server.stdout.read():
        pass
      client = subprocess.Popen(['./cwmp',
                                 '--unix-path', sockname],
                                stdin=subprocess.PIPE)
      client.stdin.close()
      self.assertEqual(client.wait(), 0)
      server.stdin.close()
      self.assertEqual(server.wait(), 0)
    finally:
      try:
        server.kill()
      except OSError:
        pass

  def testRunserver(self):
    self._DoTest(['--no-cpe'])
    self._DoTest(['--no-cpe',
                  '--platform', 'fakecpe'])
    self._DoTest(['--fake-acs',
                  '--platform', 'fakecpe'])


if __name__ == '__main__':
  unittest.main()
