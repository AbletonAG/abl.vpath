from __future__ import unicode_literals

import mimetypes
import hashlib
import time
import errno
import stat
import sys
import threading
from collections import defaultdict

from io import BytesIO

from .fs import FileSystem, BaseUri

from abl.util import Bunch, LockFileObtainException

class NodeKind(object):
    FILE = 0
    DIR = 1
    LINK = 2


class MemoryFile(object):

    kind = NodeKind.FILE

    FILE_LOCKS = defaultdict(threading.Lock)

    def __init__(self, path):
        self.path = path
        self._data = BytesIO()
        self._line_reader = None
        self.mtime = self.ctime = time.time()
        self.mode = 0
        self.lock = self.FILE_LOCKS[self.path]


    def reset(self):
        self._data = BytesIO()
        self._line_reader = None
        self.mtime = self.ctime = time.time()
        self.mode = 0
        self.lock = self.FILE_LOCKS[self.path]


    def __len__(self):
        pos = self._data.tell()
        self._data.seek(-1,2)
        length = self._data.tell() + 1
        self._data.seek(pos)
        return length


    def size(self):
        return len(self._data.getvalue())


    def write(self, d):
        self._data.write(d)
        self.mtime = time.time()


    def read(self, size=-1):
        return self._data.read(size)


    def seek(self, to, whence=0):
        self._data.seek(to, whence)


    def tell(self):
        return self._data.tell()


    def flush(self):
        return self._data.flush()


    def truncate(self, pos=None):
        return self._data.truncate(pos)


    def seekable(self):
        return self._data.seekable()


    def __unicode__(self):
        return self._data.getvalue().decode('utf-8')


    def __bytes__(self):
        return self._data.getvalue()


    def __str__(self):
        return str(self._data.getvalue())


    def close(self):
        self._line_reader = None
        self._data.seek(0)


    def readline(self):
        return self._data.readline()


    def readlines(self):
        for line in self:
            yield line


    def __next__(self):
        line = self.readline()
        if line:
            return line
        else:
            raise StopIteration


    next = __next__ # Python 2 iterator interface


    def __iter__(self):
        return self


    def items(self):
        return []


class MemoryFileProxy(object):

    def __init__(self, mem_file, readable, binary=False):
        self.mem_file = mem_file
        self.readable = readable
        self.binary = binary


    def encode(self, data):
        return data if self.binary else data.encode('utf-8')


    def decode(self, data):
        return data if self.binary else data.decode('utf-8')


    def read(self, *args, **kwargs):
        if not self.readable:
            raise IOError(errno.EBADF, "bad file descriptor")
        return self.decode(self.mem_file.read(*args, **kwargs))


    def write(self, data, *args, **kwargs):
        return self.mem_file.write(self.encode(data), *args, **kwargs)


    def __getattr__(self, name):
        return getattr(self.mem_file, name)


    def __enter__(self):
        return self


    def __exit__(self, *args):
        pass


    def __iter__(self):
        return self


    def __next__(self):
        return self.decode(next(self.mem_file))


    next = __next__ # Python 2 iterator interface


    def readline(self):
        return self.decode(self.mem_file.readline())


    def readlines(self):
        for line in self.mem_file.readlines():
            yield self.decode(line)


class MemoryDir(object):

    kind = NodeKind.DIR

    def __init__(self):
        self._files = {}
        self.mtime = self.ctime = time.time()
        self.mode = 0


    def size(self):
        return 0


    def items(self):
        return list(self._files.items())


    def keys(self):
        return list(self._files.keys())


    def has(self, name):
        return name in self._files


    def get(self, name):
        return self._files[name]


    def create(self, name, obj):
        self._files[name] = obj


    def remove(self, name):
        del self._files[name]


    def isempty(self):
        return len(self._files) == 0


class MemorySymlink(object):
    kind = NodeKind.LINK

    def __init__(self, target):
        self.target = target
        self.mtime = self.ctime = time.time()
        self.mode = 0

    def size(self):
        return 8


class MemoryFileSystemUri(BaseUri):

    def __init__(self, *args, **kwargs):
        super(MemoryFileSystemUri, self).__init__(*args, **kwargs)
        self._next_op_callback = None



class MemoryLock(object):

    def __init__(self, fs, path, fail_on_lock, cleanup):
        self.fs = fs
        self.path = path
        self.fail_on_lock = fail_on_lock
        self.cleanup = cleanup
        self.lock = None


    def __enter__(self):
        mfile = self.fs.open(self.path, "w", mimetype='application/octet-stream')
        self.lock = mfile.lock
        if self.fail_on_lock:
            if not self.lock.acquire(False):
                raise LockFileObtainException
        else:
            self.lock.acquire()
        return mfile


    def __exit__(self, unused_exc_type, unused_exc_val, unused_exc_tb):
        self.lock.release()
        if self.cleanup:
            self.path.remove()


class LookupExceptionClass(object):
    def __init__(self, fs, exc_class):
        self.fs = fs
        self.exc_class = exc_class
        self.prev_exc_class = None

    def __enter__(self):
        self.prev_exc_class = self.fs.lookup_exc_class
        self.fs.lookup_exc_class = self.exc_class
        return self

    def __exit__(self, *args):
        self.fs.lookup_exc_class = self.prev_exc_class



class MemoryFileSystem(FileSystem):

    scheme = 'memory'

    uri = MemoryFileSystemUri

    def _initialize(self):
        assert not self.hostname, "The memory schema only allows 'memory:///' as root path"
        self.lookup_exc_class = OSError
        self._fs = MemoryDir()
        self.next_op_callbacks = {}
        MemoryFile.FILE_LOCKS.clear()


    def _child(self, parent, name, resolve_link=True, throw=True, linklevel=0):
        if parent.has(name):
            nd = parent.get(name)
            if nd.kind == NodeKind.LINK:
                if resolve_link:
                    # TODO: supports absolute links only for now
                    if linklevel >= 32:
                        raise self.lookup_exc_class(errno.ELOOP,
                                                    "Too many symbolic links encountered")
                    nd = self._get_node_for_path(self._fs, nd.target, throw=throw,
                                                 linklevel=linklevel + 1)
                    if nd is None:
                        return None
                    assert nd.kind != NodeKind.LINK
            return nd
        return None

    def _create_child(self, parent, name, obj):
        parent.create(name, obj)

    def _del_child(self, parent, name):
        parent.remove(name)


    def _get_node_prev(self, base, steps, follow_link=True, throw=True,
                       linklevel=0):
        prev = None
        current = base
        for part in steps:
            prev = current
            if current.has(part):
                is_last = part == steps[-1]
                current = self._child(current, part,
                                      resolve_link=follow_link if is_last else True,
                                      throw=throw,
                                      linklevel=linklevel)
            else:
                if throw:
                    p = '/'.join(steps)
                    raise self.lookup_exc_class(errno.ENOENT,
                                                "No such file or directory: %s" % p)
                else:
                    return [None, None]
        return [prev, current]


    def _get_node(self, base, steps, follow_link=True, throw=True, linklevel=0):
        _, current = self._get_node_prev(base, steps, follow_link=follow_link, throw=throw,
                                         linklevel=linklevel)
        return current


    def _get_node_for_path(self, base, unc, follow_link=True, throw=True,
                           linklevel=0):
        p = self._path(unc)
        if p:
            return self._get_node(base, p.split("/"), follow_link=follow_link,
                                  throw=throw, linklevel=linklevel)
        else:
            return base


    def _path(self, path):
        p = super(MemoryFileSystem, self)._path(path)
        # cut off leading slash, that's our root
        assert p.startswith("/")
        p = p[1:]
        return p


    def isdir(self, path):
        if self._path(path):
            try:
                nd = self._get_node_for_path(self._fs, path, throw=False)
                if nd is None:
                    return False
                return nd.kind == NodeKind.DIR
            except OSError as e:
                if e.errno == errno.ELOOP:
                    return False

        # the root always exists and is always a dir
        return True


    def isfile(self, path):
        if self._path(path):
            try:
                nd = self._get_node_for_path(self._fs, path, throw=False)
                if nd is None:
                    return False
                return nd.kind == NodeKind.FILE
            except OSError as e:
                if e.errno == errno.ELOOP:
                    return False
        return False


    def isexec(self, path, mode_mask):
        return self.info(path).mode & mode_mask != 0


    def set_exec(self, path, mode):
        mask = stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        new_mode = (self.info(path).mode & ~mask) | mode
        self.info(path, dict(mode=new_mode))


    def mkdir(self, path):
        p = self._path(path)
        if p:
            nd = self._get_node(self._fs, p.split("/")[:-1])
            dir_to_create = p.split("/")[-1]
            if nd.has(dir_to_create):
                raise OSError(errno.EEXIST, "File exists: %r" % str(path))
            self._create_child(nd, dir_to_create, MemoryDir())


    def exists(self, path):
        if self._path(path):
            try:
                nd = self._get_node_for_path(self._fs, path, throw=False)
                if nd is None:
                    return False
            except OSError as e:
                if e.errno == errno.ELOOP:
                    return False
        # the root always exists
        return True


    def pre_call_hook(self, path, func):
        p = self._path(path)
        if p in self.next_op_callbacks and self.next_op_callbacks[p] is not None:
            self.next_op_callbacks[p](path, func)


    def _open_for_read(self, path, binary=False):
        nd = self._get_node_for_path(self._fs, path)
        nd.seek(0)
        return MemoryFileProxy(nd, True, binary=binary)


    def _open_for_write(self, path, binary=False):
        p = self._path(path)
        nd = self._get_node(self._fs, p.split("/")[:-1])
        file_to_create = p.split("/")[-1]

        if nd.has(file_to_create):
            cnd = self._child(nd, file_to_create)
            if cnd is not None and cnd.kind == NodeKind.DIR:
                raise IOError(errno.EISDIR, "File is directory" )
            cnd.reset()
            return MemoryFileProxy(cnd, False, binary=binary)
        else:
            f = MemoryFile(p)
            self._create_child(nd, file_to_create, f)
            return MemoryFileProxy(f, False, binary=binary)


    def _open_for_append(self, path, binary=False):
        nd = self._get_node_for_path(self._fs, path)
        nd.seek(len(nd))
        return MemoryFileProxy(nd, False, binary=binary)


    def open(self, path, options, mimetype):
        with LookupExceptionClass(self, IOError):
            binary = (options and "b" in options)
            if options is None or "r" in options:
                return self._open_for_read(path, binary=binary)
            elif "w" in options:
                return self._open_for_write(path, binary=binary)
            elif "a" in options:
                return self._open_for_append(path, binary=binary)
            else:
                raise OSError(errno.EINVAL, "The mode flag is not valid")


    BINARY_MIME_TYPES = ["image/png",
                         "image/gif",
                         ]

    def dump(self, outf, no_binary=False):
        def traverse(current, path="memory:///"):
            for name, value in sorted(current.items()):
                if value.kind == NodeKind.FILE:
                    if no_binary:
                        mt, _ = mimetypes.guess_type(name)
                        if mt in self.BINARY_MIME_TYPES:
                            hash_ = hashlib.md5()
                            hash_.update(value)
                            value = "Binary: %s" % hash_.hexdigest()
                    proxy = MemoryFileProxy(value, readable=True, binary=False)
                    outf.write("--- START %s%s ---\n" % (path, name))
                    outf.write(proxy.read())
                    outf.write("\n--- END ---\n\n")
                elif value.kind == NodeKind.LINK:
                    outf.write("LINK: %s%s -> %s\n" % (path, name, value.target))
                else:
                    outf.write("DIR: %s%s\n" % (path, name))
                    traverse(value,
                             (path[:-1] if path.endswith("/") else path) + "/" + name + "/")

        outf.write("MEMORY DUMP: START\n")
        traverse(self._fs)
        outf.write("MEMORY DUMP: END\n")

    def info(self, unc, set_info=None, followlinks=True):
        current = self._get_node_for_path(self._fs, unc, follow_link=followlinks)
        if set_info is not None:
            if "mode" in set_info:
                current.mode = set_info["mode"]
            if "mtime" in set_info:
                current.mtime = set_info["mtime"]
            return

        return Bunch(mtime=current.mtime,
                     mode=current.mode,
                     size=current.size())


    def copystat(self, src, dest):
        src_current = self._get_node_for_path(self._fs, src)
        dest_current = self._get_node_for_path(self._fs, dest)
        dest_current.mtime = src_current.mtime
        dest_current.mode = src_current.mode


    def listdir(self, path):
        nd = self._get_node(self._fs,
                            [x for x in self._path(path).split("/") if x])
        return sorted(nd.keys())


    def mtime(self, path):
        return self._get_node_for_path(self._fs, path).mtime


    def removefile(self, path):
        parent, _ = self._get_node_prev(self._fs,
                                        [x for x in self._path(path).split("/") if x],
                                        follow_link=False)
        if parent is not None:
            self._del_child(parent, path.last())


    def removedir(self, path):
        prev, _ = self._get_node_prev(self._fs,
                                            [x for x in self._path(path).split("/") if x])
        if prev is not None:
            part = path.last()
            if self._child(prev, part).isempty():
                self._del_child(prev, part)
            else:
                raise OSError(errno.ENOTEMPTY, "Directory not empty: %r" % path)


    def lock(self, path, fail_on_lock, cleanup):
        return MemoryLock(self, path, fail_on_lock, cleanup)


    SENTINEL = object()

    def _manipulate(self, path, lock=SENTINEL, unlock=SENTINEL, mtime=SENTINEL,
                    next_op_callback=SENTINEL):
        if lock is not self.SENTINEL and lock:
            p = self._path(path)
            lock = MemoryFile(p).lock
            res = lock.acquire()
            assert res, "you tried to double-lock a file, that's currently not supported"

        if unlock is not self.SENTINEL and unlock:
            p = self._path(path)
            lock = MemoryFile(p).lock
            lock.release()

        if mtime is not self.SENTINEL:
            nd = self._get_node_for_path(self._fs, path)
            nd.mtime = mtime

        if next_op_callback is not self.SENTINEL:
            p = self._path(path)
            self.next_op_callbacks[p] = next_op_callback


    def supports_symlinks(self):
        return True


    def islink(self, path):
        if self._path(path):
            nd = self._get_node_for_path(self._fs, path, follow_link=False,
                                         throw=False)
            if nd is None:
                return False
            return nd.kind == NodeKind.LINK
        return False


    def symlink(self, target, link_name):
        p = self._path(link_name)
        if p:
            nd = self._get_node(self._fs, p.split("/")[:-1])
            file_to_create = p.split("/")[-1]
            if nd.has(file_to_create):
                raise OSError(errno.EEXIST, "File exists: %r" % str(link_name))
            self._create_child(nd, file_to_create, MemorySymlink(target))


    def readlink(self, path):
        if self._path(path):
            nd = self._get_node_for_path(self._fs, path, follow_link=False)
            if nd.kind == NodeKind.LINK:
                return nd.target
        raise OSError(errno.EINVAL, "Not a link")
