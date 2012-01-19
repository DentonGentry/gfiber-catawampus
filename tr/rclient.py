#!/usr/bin/python
# Copyright 2011 Google Inc. All Rights Reserved.
#
# TR-069 has mandatory attribute names that don't comply with policy
#pylint: disable-msg=C6409
#
"""Command-line client for rcommand.py."""

__author__ = 'apenwarr@google.com (Avery Pennarun)'

import sys
sys.path.append('vendor/tornado')
sys.path.append('vendor/bup/lib')

import os.path
import re
import readline
import socket
import traceback
import bup.shquote
import mainloop
import quotedblock


HISTORY_FILE = os.path.expanduser('~/.rclient_history')


def Log(s, *args):
  if args:
    sys.stderr.write((s+'\n') % args)
  else:
    sys.stderr.write(s + '\n')


class Fatal(Exception):
  pass


def HandleFatal(func):
  def Fn(*args, **kwargs):
    try:
      return func(*args, **kwargs)
    except Fatal, e:
      sys.stderr.write('Fatal: %s\n' % e)
      sys.exit(1)
  return Fn


def _NormalizePath(path):
  """Like os.path.normpath, but doesn't remove any trailing slash."""
  result = os.path.normpath(path)
  if path.endswith('/') and not result.endswith('/'):
    result += '/'
  return result


def _DotsToSlashes(s):
  return re.sub(r'([^/.])\.', r'\1/', s)


def _SlashesToDots(s):
  name = s.replace('/', '.')
  if name.startswith('.'):
    name = name[1:]
  return name


class Client(object):
  """Manage the client-side state of an rcommand connection."""

  def __init__(self, loop):
    self.loop = loop
    self.stream = None
    self.result = None
    self._last_res = None
    self.cwd = '/'
    self.quotedblock = quotedblock.QuotedBlockProtocol(
        HandleFatal(self.GotBlock))
    self._StartConnect()

  def _StartConnect(self):
    self.stream = None
    try:
      self.loop.ConnectUnix('/tmp/mainloop.sock',
                            HandleFatal(self.OnConnect))
    except socket.error, e:
      raise Fatal(str(e))

  def Close(self):
    if self.stream:
      self.stream.close()

  def OnConnect(self, stream):
    print 'Connected to server.'
    self.stream = stream
    self.stream.set_close_callback(HandleFatal(self.OnClose))
    self._StartRead()
    self.loop.ioloop.stop()

  def _StartRead(self):
    self.stream.read_until('\n', HandleFatal(self.GotData))

  def OnClose(self):
    print 'Server connection closed!'
    self._StartConnect()

  def GotData(self, data):
    self.quotedblock.GotData(data)
    self._StartRead()

  def GotBlock(self, lines):
    self.result = lines
    self.loop.ioloop.stop()

  def Send(self, lines):
    s = self.quotedblock.RenderBlock(lines)
    self.stream.write(s)

  def Run(self, lines):
    self.Send(lines)
    self.loop.Start()
    result = self.result
    self.result = None
    return result

  def _RequestCompletions(self, prefix):
    prefix = _NormalizePath(prefix)
    completions = self.Run([['completions', _SlashesToDots(prefix)]])[1:]
    for [i] in completions:
      yield i

  def _GetSubstitutions(self, line):
    (qtype, lastword) = bup.shquote.unfinished_word(line)
    request = os.path.join(self.cwd, _DotsToSlashes(lastword))
    subs = list(self._RequestCompletions(request))
    cmd = line.split(' ', 1)[0]
    if cmd.lower() in ('cd', 'ls', 'list', 'rlist', 'add', 'del'):
      # only return object names, not parameters
      subs = [i for i in subs if i.endswith('.')]
    return (qtype, lastword, subs)

  def _StripPathPrefix(self, oldword, newword):
    # readline is weird: we have to remove all the parts that were before
    # the last '/', but not parts before the last '.', because we have to
    # tell it what to replace everything after the last '/' with.
    after_slash = oldword.split('/')[-1]
    dots = after_slash.split('.')
    if newword.endswith('.'):
      new_last_dot = '.'.join(newword.split('.')[-2:])
    else:
      new_last_dot = newword.split('.')[-1]
    dots[-1] = new_last_dot
    return '.'.join(dots)

  def ReadlineCompleter(self, text, state):
    """Callback for the readline library to autocomplete a line of text.

    Args:
      text: the current input word (basename following the last slash)
      state: a number of 0..n, where n is the number of substitutions.
    Returns:
      One of the available substitutions.
    """
    try:
      text = _DotsToSlashes(text)
      line = readline.get_line_buffer()[:readline.get_endidx()]
      if not state:
        self._last_res = self._GetSubstitutions(line)
      (qtype, lastword, subs) = self._last_res
      if state < len(subs):
        new_last_slash = _DotsToSlashes(self._StripPathPrefix(lastword,
                                                              subs[state]))
        is_param = not new_last_slash.endswith('/')
        if is_param and qtype:
          new_last_slash += qtype
        return new_last_slash
    except Exception, e:  #pylint: disable-msg=W0703
      Log('\n')
      try:
        traceback.print_tb(sys.exc_traceback)
      except Exception, e2:  #pylint: disable-msg=W0703
        Log('Error printing traceback: %s\n' % e2)
    Log('\nError in completion: %s\n' % e)


def main():
  if os.path.exists(HISTORY_FILE):
    readline.read_history_file(HISTORY_FILE)
  client = None
  try:  #pylint: disable-msg=C6405
    loop = mainloop.MainLoop()
    client = Client(loop)
    loop.Start()

    readline.set_completer_delims(' \t\n\r/')
    readline.set_completer(client.ReadlineCompleter)
    readline.parse_and_bind('tab: complete')

    while True:
      print
      line = raw_input('%s> ' % client.cwd) + '\n'
      while 1:
        word = bup.shquote.unfinished_word(line)[1]
        if not word:
          break
        line += raw_input('%*s> ' % (len(client.cwd), '')) + '\n'
      #pylint: disable-msg=W0612
      words = [word for (idx, word) in bup.shquote.quotesplit(line)]
      if not words:
        continue
      cmd, args = (words[0].lower(), words[1:])
      if cmd in ('cd', 'ls', 'list', 'rlist', 'add', 'del', 'get', 'set'):
        if not args:
          args = [client.cwd]
        relpath = _DotsToSlashes(args[0])
        abspath = os.path.normpath(os.path.join(client.cwd, relpath))
        args[0] = _SlashesToDots(abspath)
      if cmd == 'cd':
        client.cwd = os.path.normpath(os.path.join(client.cwd, relpath))
      else:
        line = [cmd] + args
        result = client.Run([line])
        print client.quotedblock.RenderBlock(result).strip()
  except Fatal, e:
    sys.stderr.write('%s\n' % e)
    sys.exit(1)
  finally:
    readline.write_history_file(HISTORY_FILE)
    if client:
      client.Close()


if __name__ == '__main__':
  main()
