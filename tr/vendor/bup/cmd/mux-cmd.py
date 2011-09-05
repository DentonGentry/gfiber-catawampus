#!/usr/bin/env python
import os, sys, subprocess, struct
from bup import options
from bup.helpers import *

optspec = """
bup mux command [command arguments...]
--
"""
o = options.Options(optspec)
(opt, flags, extra) = o.parse(sys.argv[1:])
if len(extra) < 1:
    o.fatal('command is required')

cmdpath, cmdfn = os.path.split(__file__)
subcmd = extra
subcmd[0] = os.path.join(cmdpath, 'bup-' + subcmd[0])

debug2('bup mux: starting %r\n' % (extra,))

outr, outw = os.pipe()
errr, errw = os.pipe()
def close_fds():
    os.close(outr)
    os.close(errr)
p = subprocess.Popen(subcmd, stdout=outw, stderr=errw, preexec_fn=close_fds)
os.close(outw)
os.close(errw)
sys.stdout.write('BUPMUX')
sys.stdout.flush()
mux(p, sys.stdout.fileno(), outr, errr)
os.close(outr)
os.close(errr)
prv = p.wait()

if prv:
    debug1('%s exited with code %d\n' % (extra[0], prv))

debug1('bup mux: done\n')

sys.exit(prv)
