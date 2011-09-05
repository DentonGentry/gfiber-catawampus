"""Helper functions and classes for bup."""

import sys, os, pwd, subprocess, errno, socket, select, mmap, stat, re, struct
import heapq, operator, time, platform
from bup import _version, _helpers
import bup._helpers as _helpers

# This function should really be in helpers, not in bup.options.  But we
# want options.py to be standalone so people can include it in other projects.
from bup.options import _tty_width
tty_width = _tty_width


def atoi(s):
    """Convert the string 's' to an integer. Return 0 if s is not a number."""
    try:
        return int(s or '0')
    except ValueError:
        return 0


def atof(s):
    """Convert the string 's' to a float. Return 0 if s is not a number."""
    try:
        return float(s or '0')
    except ValueError:
        return 0


buglvl = atoi(os.environ.get('BUP_DEBUG', 0))


# Write (blockingly) to sockets that may or may not be in blocking mode.
# We need this because our stderr is sometimes eaten by subprocesses
# (probably ssh) that sometimes make it nonblocking, if only temporarily,
# leading to race conditions.  Ick.  We'll do it the hard way.
def _hard_write(fd, buf):
    while buf:
        (r,w,x) = select.select([], [fd], [], None)
        if not w:
            raise IOError('select(fd) returned without being writable')
        try:
            sz = os.write(fd, buf)
        except OSError, e:
            if e.errno != errno.EAGAIN:
                raise
        assert(sz >= 0)
        buf = buf[sz:]


_last_prog = 0
def log(s):
    """Print a log message to stderr."""
    global _last_prog
    sys.stdout.flush()
    _hard_write(sys.stderr.fileno(), s)
    _last_prog = 0


def debug1(s):
    if buglvl >= 1:
        log(s)


def debug2(s):
    if buglvl >= 2:
        log(s)


istty1 = os.isatty(1) or (atoi(os.environ.get('BUP_FORCE_TTY')) & 1)
istty2 = os.isatty(2) or (atoi(os.environ.get('BUP_FORCE_TTY')) & 2)
_last_progress = ''
def progress(s):
    """Calls log() if stderr is a TTY.  Does nothing otherwise."""
    global _last_progress
    if istty2:
        log(s)
        _last_progress = s


def qprogress(s):
    """Calls progress() only if we haven't printed progress in a while.
    
    This avoids overloading the stderr buffer with excess junk.
    """
    global _last_prog
    now = time.time()
    if now - _last_prog > 0.1:
        progress(s)
        _last_prog = now


def reprogress():
    """Calls progress() to redisplay the most recent progress message.

    Useful after you've printed some other message that wipes out the
    progress line.
    """
    if _last_progress and _last_progress.endswith('\r'):
        progress(_last_progress)


def mkdirp(d, mode=None):
    """Recursively create directories on path 'd'.

    Unlike os.makedirs(), it doesn't raise an exception if the last element of
    the path already exists.
    """
    try:
        if mode:
            os.makedirs(d, mode)
        else:
            os.makedirs(d)
    except OSError, e:
        if e.errno == errno.EEXIST:
            pass
        else:
            raise


def next(it):
    """Get the next item from an iterator, None if we reached the end."""
    try:
        return it.next()
    except StopIteration:
        return None


def merge_iter(iters, pfreq, pfunc, pfinal, key=None):
    if key:
        samekey = lambda e, pe: getattr(e, key) == getattr(pe, key, None)
    else:
        samekey = operator.eq
    count = 0
    total = sum(len(it) for it in iters)
    iters = (iter(it) for it in iters)
    heap = ((next(it),it) for it in iters)
    heap = [(e,it) for e,it in heap if e]

    heapq.heapify(heap)
    pe = None
    while heap:
        if not count % pfreq:
            pfunc(count, total)
        e, it = heap[0]
        if not samekey(e, pe):
            pe = e
            yield e
        count += 1
        try:
            e = it.next() # Don't use next() function, it's too expensive
        except StopIteration:
            heapq.heappop(heap) # remove current
        else:
            heapq.heapreplace(heap, (e, it)) # shift current to new location
    pfinal(count, total)


def unlink(f):
    """Delete a file at path 'f' if it currently exists.

    Unlike os.unlink(), does not throw an exception if the file didn't already
    exist.
    """
    try:
        os.unlink(f)
    except OSError, e:
        if e.errno == errno.ENOENT:
            pass  # it doesn't exist, that's what you asked for


def readpipe(argv):
    """Run a subprocess and return its output."""
    p = subprocess.Popen(argv, stdout=subprocess.PIPE)
    r = p.stdout.read()
    p.wait()
    return r


def realpath(p):
    """Get the absolute path of a file.

    Behaves like os.path.realpath, but doesn't follow a symlink for the last
    element. (ie. if 'p' itself is a symlink, this one won't follow it, but it
    will follow symlinks in p's directory)
    """
    try:
        st = os.lstat(p)
    except OSError:
        st = None
    if st and stat.S_ISLNK(st.st_mode):
        (dir, name) = os.path.split(p)
        dir = os.path.realpath(dir)
        out = os.path.join(dir, name)
    else:
        out = os.path.realpath(p)
    #log('realpathing:%r,%r\n' % (p, out))
    return out


def detect_fakeroot():
    "Return True if we appear to be running under fakeroot."
    return os.getenv("FAKEROOTKEY") != None


def is_superuser():
    if platform.system().startswith('CYGWIN'):
        import ctypes
        return ctypes.cdll.shell32.IsUserAnAdmin()
    else:
        return os.geteuid() == 0


_username = None
def username():
    """Get the user's login name."""
    global _username
    if not _username:
        uid = os.getuid()
        try:
            _username = pwd.getpwuid(uid)[0]
        except KeyError:
            _username = 'user%d' % uid
    return _username


_userfullname = None
def userfullname():
    """Get the user's full name."""
    global _userfullname
    if not _userfullname:
        uid = os.getuid()
        try:
            _userfullname = pwd.getpwuid(uid)[4].split(',')[0]
        except KeyError:
            _userfullname = 'user%d' % uid
    return _userfullname


_hostname = None
def hostname():
    """Get the FQDN of this machine."""
    global _hostname
    if not _hostname:
        _hostname = socket.getfqdn()
    return _hostname


_resource_path = None
def resource_path(subdir=''):
    global _resource_path
    if not _resource_path:
        _resource_path = os.environ.get('BUP_RESOURCE_PATH') or '.'
    return os.path.join(_resource_path, subdir)


class NotOk(Exception):
    pass


class BaseConn:
    def __init__(self, outp):
        self.outp = outp

    def close(self):
        while self._read(65536): pass

    def read(self, size):
        """Read 'size' bytes from input stream."""
        self.outp.flush()
        return self._read(size)

    def readline(self):
        """Read from input stream until a newline is found."""
        self.outp.flush()
        return self._readline()

    def write(self, data):
        """Write 'data' to output stream."""
        #log('%d writing: %d bytes\n' % (os.getpid(), len(data)))
        self.outp.write(data)

    def has_input(self):
        """Return true if input stream is readable."""
        raise NotImplemented("Subclasses must implement has_input")

    def ok(self):
        """Indicate end of output from last sent command."""
        self.write('\nok\n')

    def error(self, s):
        """Indicate server error to the client."""
        s = re.sub(r'\s+', ' ', str(s))
        self.write('\nerror %s\n' % s)

    def _check_ok(self, onempty):
        self.outp.flush()
        rl = ''
        for rl in linereader(self):
            #log('%d got line: %r\n' % (os.getpid(), rl))
            if not rl:  # empty line
                continue
            elif rl == 'ok':
                return None
            elif rl.startswith('error '):
                #log('client: error: %s\n' % rl[6:])
                return NotOk(rl[6:])
            else:
                onempty(rl)
        raise Exception('server exited unexpectedly; see errors above')

    def drain_and_check_ok(self):
        """Remove all data for the current command from input stream."""
        def onempty(rl):
            pass
        return self._check_ok(onempty)

    def check_ok(self):
        """Verify that server action completed successfully."""
        def onempty(rl):
            raise Exception('expected "ok", got %r' % rl)
        return self._check_ok(onempty)


class Conn(BaseConn):
    def __init__(self, inp, outp):
        BaseConn.__init__(self, outp)
        self.inp = inp

    def _read(self, size):
        return self.inp.read(size)

    def _readline(self):
        return self.inp.readline()

    def has_input(self):
        [rl, wl, xl] = select.select([self.inp.fileno()], [], [], 0)
        if rl:
            assert(rl[0] == self.inp.fileno())
            return True
        else:
            return None


def checked_reader(fd, n):
    while n > 0:
        rl, _, _ = select.select([fd], [], [])
        assert(rl[0] == fd)
        buf = os.read(fd, n)
        if not buf: raise Exception("Unexpected EOF reading %d more bytes" % n)
        yield buf
        n -= len(buf)


MAX_PACKET = 128 * 1024
def mux(p, outfd, outr, errr):
    try:
        fds = [outr, errr]
        while p.poll() is None:
            rl, _, _ = select.select(fds, [], [])
            for fd in rl:
                if fd == outr:
                    buf = os.read(outr, MAX_PACKET)
                    if not buf: break
                    os.write(outfd, struct.pack('!IB', len(buf), 1) + buf)
                elif fd == errr:
                    buf = os.read(errr, 1024)
                    if not buf: break
                    os.write(outfd, struct.pack('!IB', len(buf), 2) + buf)
    finally:
        os.write(outfd, struct.pack('!IB', 0, 3))


class DemuxConn(BaseConn):
    """A helper class for bup's client-server protocol."""
    def __init__(self, infd, outp):
        BaseConn.__init__(self, outp)
        # Anything that comes through before the sync string was not
        # multiplexed and can be assumed to be debug/log before mux init.
        tail = ''
        while tail != 'BUPMUX':
            b = os.read(infd, (len(tail) < 6) and (6-len(tail)) or 1)
            if not b:
                raise IOError('demux: unexpected EOF during initialization')
            tail += b
            sys.stderr.write(tail[:-6])  # pre-mux log messages
            tail = tail[-6:]
        self.infd = infd
        self.reader = None
        self.buf = None
        self.closed = False

    def write(self, data):
        self._load_buf(0)
        BaseConn.write(self, data)

    def _next_packet(self, timeout):
        if self.closed: return False
        rl, wl, xl = select.select([self.infd], [], [], timeout)
        if not rl: return False
        assert(rl[0] == self.infd)
        ns = ''.join(checked_reader(self.infd, 5))
        n, fdw = struct.unpack('!IB', ns)
        assert(n <= MAX_PACKET)
        if fdw == 1:
            self.reader = checked_reader(self.infd, n)
        elif fdw == 2:
            for buf in checked_reader(self.infd, n):
                sys.stderr.write(buf)
        elif fdw == 3:
            self.closed = True
            debug2("DemuxConn: marked closed\n")
        return True

    def _load_buf(self, timeout):
        if self.buf is not None:
            return True
        while not self.closed:
            while not self.reader:
                if not self._next_packet(timeout):
                    return False
            try:
                self.buf = self.reader.next()
                return True
            except StopIteration:
                self.reader = None
        return False

    def _read_parts(self, ix_fn):
        while self._load_buf(None):
            assert(self.buf is not None)
            i = ix_fn(self.buf)
            if i is None or i == len(self.buf):
                yv = self.buf
                self.buf = None
            else:
                yv = self.buf[:i]
                self.buf = self.buf[i:]
            yield yv
            if i is not None:
                break

    def _readline(self):
        def find_eol(buf):
            try:
                return buf.index('\n')+1
            except ValueError:
                return None
        return ''.join(self._read_parts(find_eol))

    def _read(self, size):
        csize = [size]
        def until_size(buf): # Closes on csize
            if len(buf) < csize[0]:
                csize[0] -= len(buf)
                return None
            else:
                return csize[0]
        return ''.join(self._read_parts(until_size))

    def has_input(self):
        return self._load_buf(0)


def linereader(f):
    """Generate a list of input lines from 'f' without terminating newlines."""
    while 1:
        line = f.readline()
        if not line:
            break
        yield line[:-1]


def chunkyreader(f, count = None):
    """Generate a list of chunks of data read from 'f'.

    If count is None, read until EOF is reached.

    If count is a positive integer, read 'count' bytes from 'f'. If EOF is
    reached while reading, raise IOError.
    """
    if count != None:
        while count > 0:
            b = f.read(min(count, 65536))
            if not b:
                raise IOError('EOF with %d bytes remaining' % count)
            yield b
            count -= len(b)
    else:
        while 1:
            b = f.read(65536)
            if not b: break
            yield b


def slashappend(s):
    """Append "/" to 's' if it doesn't aleady end in "/"."""
    if s and not s.endswith('/'):
        return s + '/'
    else:
        return s


def _mmap_do(f, sz, flags, prot, close):
    if not sz:
        st = os.fstat(f.fileno())
        sz = st.st_size
    if not sz:
        # trying to open a zero-length map gives an error, but an empty
        # string has all the same behaviour of a zero-length map, ie. it has
        # no elements :)
        return ''
    map = mmap.mmap(f.fileno(), sz, flags, prot)
    if close:
        f.close()  # map will persist beyond file close
    return map


def mmap_read(f, sz = 0, close=True):
    """Create a read-only memory mapped region on file 'f'.
    If sz is 0, the region will cover the entire file.
    """
    return _mmap_do(f, sz, mmap.MAP_PRIVATE, mmap.PROT_READ, close)


def mmap_readwrite(f, sz = 0, close=True):
    """Create a read-write memory mapped region on file 'f'.
    If sz is 0, the region will cover the entire file.
    """
    return _mmap_do(f, sz, mmap.MAP_SHARED, mmap.PROT_READ|mmap.PROT_WRITE,
                    close)


def mmap_readwrite_private(f, sz = 0, close=True):
    """Create a read-write memory mapped region on file 'f'.
    If sz is 0, the region will cover the entire file.
    The map is private, which means the changes are never flushed back to the
    file.
    """
    return _mmap_do(f, sz, mmap.MAP_PRIVATE, mmap.PROT_READ|mmap.PROT_WRITE,
                    close)


def parse_num(s):
    """Parse data size information into a float number.

    Here are some examples of conversions:
        199.2k means 203981 bytes
        1GB means 1073741824 bytes
        2.1 tb means 2199023255552 bytes
    """
    g = re.match(r'([-+\d.e]+)\s*(\w*)', str(s))
    if not g:
        raise ValueError("can't parse %r as a number" % s)
    (val, unit) = g.groups()
    num = float(val)
    unit = unit.lower()
    if unit in ['t', 'tb']:
        mult = 1024*1024*1024*1024
    elif unit in ['g', 'gb']:
        mult = 1024*1024*1024
    elif unit in ['m', 'mb']:
        mult = 1024*1024
    elif unit in ['k', 'kb']:
        mult = 1024
    elif unit in ['', 'b']:
        mult = 1
    else:
        raise ValueError("invalid unit %r in number %r" % (unit, s))
    return int(num*mult)


def count(l):
    """Count the number of elements in an iterator. (consumes the iterator)"""
    return reduce(lambda x,y: x+1, l)


saved_errors = []
def add_error(e):
    """Append an error message to the list of saved errors.

    Once processing is able to stop and output the errors, the saved errors are
    accessible in the module variable helpers.saved_errors.
    """
    saved_errors.append(e)
    log('%-70s\n' % e)


def clear_errors():
    global saved_errors
    saved_errors = []


def handle_ctrl_c():
    """Replace the default exception handler for KeyboardInterrupt (Ctrl-C).

    The new exception handler will make sure that bup will exit without an ugly
    stacktrace when Ctrl-C is hit.
    """
    oldhook = sys.excepthook
    def newhook(exctype, value, traceback):
        if exctype == KeyboardInterrupt:
            log('Interrupted.\n')
        else:
            return oldhook(exctype, value, traceback)
    sys.excepthook = newhook


def columnate(l, prefix):
    """Format elements of 'l' in columns with 'prefix' leading each line.

    The number of columns is determined automatically based on the string
    lengths.
    """
    if not l:
        return ""
    l = l[:]
    clen = max(len(s) for s in l)
    ncols = (tty_width() - len(prefix)) / (clen + 2)
    if ncols <= 1:
        ncols = 1
        clen = 0
    cols = []
    while len(l) % ncols:
        l.append('')
    rows = len(l)/ncols
    for s in range(0, len(l), rows):
        cols.append(l[s:s+rows])
    out = ''
    for row in zip(*cols):
        out += prefix + ''.join(('%-*s' % (clen+2, s)) for s in row) + '\n'
    return out


def parse_date_or_fatal(str, fatal):
    """Parses the given date or calls Option.fatal().
    For now we expect a string that contains a float."""
    try:
        date = atof(str)
    except ValueError, e:
        raise fatal('invalid date format (should be a float): %r' % e)
    else:
        return date


def strip_path(prefix, path):
    """Strips a given prefix from a path.

    First both paths are normalized.

    Raises an Exception if no prefix is given.
    """
    if prefix == None:
        raise Exception('no path given')

    normalized_prefix = os.path.realpath(prefix)
    debug2("normalized_prefix: %s\n" % normalized_prefix)
    normalized_path = os.path.realpath(path)
    debug2("normalized_path: %s\n" % normalized_path)
    if normalized_path.startswith(normalized_prefix):
        return normalized_path[len(normalized_prefix):]
    else:
        return path


def strip_base_path(path, base_paths):
    """Strips the base path from a given path.


    Determines the base path for the given string and then strips it
    using strip_path().
    Iterates over all base_paths from long to short, to prevent that
    a too short base_path is removed.
    """
    normalized_path = os.path.realpath(path)
    sorted_base_paths = sorted(base_paths, key=len, reverse=True)
    for bp in sorted_base_paths:
        if normalized_path.startswith(os.path.realpath(bp)):
            return strip_path(bp, normalized_path)
    return path


def graft_path(graft_points, path):
    normalized_path = os.path.realpath(path)
    for graft_point in graft_points:
        old_prefix, new_prefix = graft_point
        if normalized_path.startswith(old_prefix):
            return re.sub(r'^' + old_prefix, new_prefix, normalized_path)
    return normalized_path


# hashlib is only available in python 2.5 or higher, but the 'sha' module
# produces a DeprecationWarning in python 2.6 or higher.  We want to support
# python 2.4 and above without any stupid warnings, so let's try using hashlib
# first, and downgrade if it fails.
try:
    import hashlib
except ImportError:
    import sha
    Sha1 = sha.sha
else:
    Sha1 = hashlib.sha1


def version_date():
    """Format bup's version date string for output."""
    return _version.DATE.split(' ')[0]


def version_commit():
    """Get the commit hash of bup's current version."""
    return _version.COMMIT


def version_tag():
    """Format bup's version tag (the official version number).

    When generated from a commit other than one pointed to with a tag, the
    returned string will be "unknown-" followed by the first seven positions of
    the commit hash.
    """
    names = _version.NAMES.strip()
    assert(names[0] == '(')
    assert(names[-1] == ')')
    names = names[1:-1]
    l = [n.strip() for n in names.split(',')]
    for n in l:
        if n.startswith('tag: bup-'):
            return n[9:]
    return 'unknown-%s' % _version.COMMIT[:7]
