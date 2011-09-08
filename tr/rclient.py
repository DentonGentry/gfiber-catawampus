#!/usr/bin/python
# Copyright 2011 Google Inc. All Rights Reserved.
#
# TR-069 has mandatory attribute names that don't comply with policy
#pylint: disable-msg=C6409
#
"""Command-line client for rcommand.py."""

__author__ = 'apenwarr@google.com (Avery Pennarun)'


import os.path
import re
import readline
import socket
import sys
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


def _DotsToSlashes(s):
  return re.sub(r'([^/.])\.', r'\1/', s)


def _SlashesToDots(s):
  name = s.replace('/', '.')
  if name.startswith('.'):
    name = name[1:]
  return name


class Client(object):
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
    return self.result

  def _GetSubstitutions(self, line):
    (qtype, lastword) = bup.shquote.unfinished_word(line)
    prefix = _SlashesToDots(self.cwd)
    if prefix and not prefix.endswith('.'):
      prefix += '.'
    fullpath = prefix + _SlashesToDots(lastword)
    result = self.Run([['completions', fullpath]])
    subs = [_DotsToSlashes(i[0][len(prefix):]) for i in result[1:]]
    cmd, rest = line.split(' ', 1)
    if cmd.lower() in ('cd', 'ls', 'list', 'rlist', 'add'):
      # only return object names, not parameters
      subs = [i for i in subs if i.endswith('/')]
    return (qtype, _DotsToSlashes(lastword), subs)

  def ReadlineCompleter(self, text, state):
    try:
      text = _DotsToSlashes(text)
      line = readline.get_line_buffer()[:readline.get_endidx()]
      if not state:
        self._last_res = self._GetSubstitutions(line)
      (qtype, lastword, subs) = self._last_res
      if state < len(subs):
        is_param = not subs[state].endswith('.')
        ret = bup.shquote.what_to_add(qtype, lastword, subs[state],
                                      terminate=is_param)
        return text + ret
    except Exception, e:
      Log('\n')
      try:
        import traceback
        traceback.print_tb(sys.exc_traceback)
      except Exception, e2:
        Log('Error printing traceback: %s\n' % e2)
    Log('\nError in completion: %s\n' % e)


def main():
  if os.path.exists(HISTORY_FILE):
    readline.read_history_file(HISTORY_FILE)
  client = None
  try:
    loop = mainloop.MainLoop()
    client = Client(loop)
    loop.Start()

    readline.set_completer_delims(' \t\n\r/')
    readline.set_completer(client.ReadlineCompleter)
    readline.parse_and_bind("tab: complete")
    
    while True:
      print
      line = raw_input('%s> ' % client.cwd) + '\n'
      while 1:
        wordstart, word = bup.shquote.unfinished_word(line)
        if not word:
          break
        line += raw_input('%*s> ' % (len(client.cwd), '')) + '\n'
      words = [word for (idx, word) in bup.shquote.quotesplit(line)]
      if not words:
        continue
      cmd, args = (words[0].lower(), words[1:])
      if cmd in ('cd', 'ls', 'list', 'rlist', 'get', 'set'):
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
