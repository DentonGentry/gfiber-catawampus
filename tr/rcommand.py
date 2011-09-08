#!/usr/bin/python
# Copyright 2011 Google Inc. All Rights Reserved.
#
# TR-069 has mandatory attribute names that don't comply with policy
#pylint: disable-msg=C6409
#
"""A simple command protocol that lets us manipulate a TR-069 tree."""

__author__ = 'apenwarr@google.com (Avery Pennarun)'


import traceback
import core
import mainloop
import quotedblock


class RemoteCommandStreamer(quotedblock.QuotedBlockStreamer):
  """A simple command protocol that lets us manipulate a TR-069 tree."""

  def __init__(self, sock, address, root):
    """Initialize a RemoteCommandStreamer.

    Args:
      sock: the socket provided by mainloop.Listen
      address: the address provided by mainloop.Listen
      root: the root of the TR-069 (core.Exporter) object tree.
    """
    quotedblock.QuotedBlockStreamer.__init__(self, sock, address)
    self.root = root

  def _ProcessBlock(self, lines):
    if not lines:
      raise Exception('try the "help" command')
    for words in lines:
      cmd, args = words[0], tuple(words[1:])
      funcname = 'Cmd%s' % cmd.title()
      print 'command: %r %r' % (cmd, args)
      func = getattr(self, funcname, None)
      if not func:
        raise Exception('no such command %r' % (cmd,))
      yield func(*args)

  def ProcessBlock(self, lines):
    """Process an incoming list of commands and return the result."""
    try:
      out = sum((list(i) for i in self._ProcessBlock(lines)), [])
    except EOFError:
      raise
    except Exception, e:
      print traceback.format_exc()
      return [['ERROR', '-1', str(e)]]
    return [['OK']] + out

  def CmdHelp(self):
    """Return a list of available commands."""
    for name in sorted(dir(self)):
      if name.startswith('Cmd'):
        func = getattr(self, name)
        yield [name[3:].lower(), func.__doc__ or '']

  def CmdQuit(self):
    """Close the current connection."""
    raise EOFError()

  def CmdGet(self, name):
    """Get the value of the given parameter."""
    return [[name, self.root.GetExport(name)]]

  def CmdSet(self, name, value):
    """Set the given parameter to the given value."""
    self.root.SetExportParam(name, value)
    return [[name, value]]

  def _CmdList(self, name, recursive):
    prefix = name and ('%s.' % name) or ''
    for k in self.root.ListExports(name, recursive=recursive):
      if k.endswith('.'):
        yield [k]
      else:
        yield [k, self.root.GetExport(prefix + k)]

  def CmdList(self, name=None):
    """Return a list of objects, non-recursively starting at the given name."""
    return self._CmdList(name, recursive=False)

  CmdLs = CmdList

  def CmdRlist(self, name=None):
    """Return a list of objects, recursively starting at the given name."""
    return self._CmdList(name, recursive=True)

  def CmdAdd(self, name, idx=None):
    """Add a sub-object to the given list with the given (optional) index."""
    #pylint: disable-msg=W0612
    idx, obj = self.root.AddExportObject(name, idx)
    return [[idx]]

  def CmdDel(self, name, *idxlist):
    """Delete one or more sub-objects from the given list."""
    for idx in idxlist:
      self.root.DeleteExportObject(name, idx)
      yield [idx]


def MakeRemoteCommandStreamer(root):
  def Fn(sock, address):
    return RemoteCommandStreamer(sock, address, root)
  return Fn


def main():
  loop = mainloop.MainLoop()

  class Sub(core.Exporter):
    def __init__(self):
      core.Exporter.__init__(self)
      self.Export(params=['Value'])
      self.Value = 0

  root = core.Exporter()
  root.Sub = Sub
  root.SubList = {}
  root.Test = 'this is a test string'
  root.Export(params=['Test'], lists=['Sub'])

  loop.ListenInet6(('', 12999), MakeRemoteCommandStreamer(root))
  loop.ListenUnix('/tmp/mainloop.sock', MakeRemoteCommandStreamer(root))
  loop.Start()


if __name__ == '__main__':
  main()
