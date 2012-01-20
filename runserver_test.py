#!/usr/bin/python
#
# Copyright 2011 Google Inc. All Rights Reserved.
#
# unittest requires method names starting in 'test'
#pylint: disable-msg=C6409

"""Unit tests for runserver.py."""

__author__ = 'apenwarr@google.com (Avery Pennarun)'

import tr.fix_path

import unittest
import subprocess


class RunserverTest(unittest.TestCase):
  """Tests for runserver.py and tr/rclient.py."""

  def testRunserver(self):
    server = subprocess.Popen(['./runserver.py',
                               '--no-cpe', '--close-stdio',
                               '--platform=fakecpe'],
                              stdout=subprocess.PIPE, stdin=subprocess.PIPE)
    try:
      while server.stdout.read():
        pass
      client = subprocess.Popen(['tr/rclient.py'], stdin=subprocess.PIPE)
      client.stdin.close()
      self.assertEqual(client.wait(), 0)
      server.stdin.close()
      self.assertEqual(server.wait(), 0)
    finally:
      try:
        server.kill()
      except OSError:
        pass


if __name__ == '__main__':
  unittest.main()
