from __future__ import absolute_import

import mimetypes
import hashlib
import time
import errno
import stat
import threading

from cStringIO import StringIO

from .fs import FileSystem, BaseUri, URI
from .exceptions import FileDoesNotExistError

from abl.util import Bunch, LockFileObtainException

class NodeKind(object):
    FILE = 0
    DIR = 1


class MemoryFile(object):

    kind = NodeKind.FILE

    FILE_LOCKS = {}

    def __init__(self, fs, path):
        self.path = path
        self.fs = path
        self._data = StringIO()
        self._line_reader = None
        self.mtime = self.ctime = time.time()
        self.mode = 0
        self.lock = self.FILE_LOCKS.setdefault((self.fs, self.path), threading.Lock())


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


    def __str__(self):
        return self._data.getvalue()


    def close(self):
        self._line_reader = None
        self._data.seek(0)


    def readline(self):
        return self._data.readline()


    def readlines(self):
        for line in self:
            yield line


    def next(self):
        line = self.readline()
        if line:
            return line
        else:
            raise StopIteration


    def __iter__(self):
        return self


    def items(self):
        return []


class MemoryFileProxy(object):

    def __init__(self, mem_file, readable):
        self.mem_file, self.readable = mem_file, readable


    def read(self, *args, **kwargs):
        if not self.readable:
            raise IOError(9, "bad file descriptor")
        return self.mem_file.read(*args, **kwargs)


    def __getattr__(self, name):
        return getattr(self.mem_file, name)


    def __enter__(self):
        return self


    def __exit__(self, *args):
        pass


    def __iter__(self):
        return self.mem_file


class MemoryDir(object):

    kind = NodeKind.DIR

    def __init__(self):
        self._files = {}
        self.mtime = self.ctime = time.time()
        self.mode = 0


    def size(self):
        return 0


    def items(self):
        return self._files.items()


    def keys(self):
        return self._files.keys()


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



class MemoryFileSystem(FileSystem):

    scheme = 'memory'

    uri = MemoryFileSystemUri

    def _initialize(self):
        self._fs = MemoryDir()
        self.next_op_callbacks = {}


    def _child(self, parent, name):
        return parent.get(name) if parent.has(name) else None

    def _create_child(self, parent, name, obj):
        parent.create(name, obj)

    def _del_child(self, parent, name):
        parent.remove(name)


    def _get_node_prev(self, base, steps, throw=True):
        prev = None
        current = base
        for part in steps:
            prev = current
            if current.has(part):
                current = self._child(current, part)
            else:
                if throw:
                    raise OSError(errno.ENOENT,
                                  "No such file or directory: %s" % '/'.join(steps))
                else:
                    return [None, None]
        return [prev, current]


    def _get_node(self, base, steps, throw=True):
        _, current = self._get_node_prev(base, steps, throw=throw)
        return current


    def _get_node_for_path(self, base, unc, throw=True):
        p = self._path(unc)
        if p:
            return self._get_node(base, p.split("/"), throw=throw)
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
            nd = self._get_node_for_path(self._fs, path, throw=False)
            if nd is None:
                return False
            return nd.kind == NodeKind.DIR
        # the root always exists and is always a dir
        return True


    def isfile(self, path):
        if self._path(path):
            nd = self._get_node_for_path(self._fs, path, throw=False)
            if nd is None:
                return False
            return nd.kind == NodeKind.FILE
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
            nd = self._get_node_for_path(self._fs, path, throw=False)
            if nd is None:
                return False
        # the root always exists
        return True


    def pre_call_hook(self, path, func):
        p = self._path(path)
        if p in self.next_op_callbacks and self.next_op_callbacks[p] is not None:
            self.next_op_callbacks[p](path, func)


    def open(self, path, options, mimetype):
        p = self._path(path)
        current = self._get_node(self._fs, p.split("/")[:-1])
        readable = False
        file_to_create = p.split("/")[-1]

        if options is None or "r" in options:
            f = self._child(current, file_to_create)
            f.seek(0)
            readable = True

        elif "w" in options or not current.has(file_to_create):
            c = self._child(current, file_to_create)
            if c is not None and c.kind == NodeKind.DIR:
                raise IOError(errno.EISDIR, "File is directory" )
            f = MemoryFile(self, p)
            self._create_child(current, file_to_create, f)

        elif "a" in options:
            f = self._child(current, file_to_create)
            f.seek(len(f))

        return MemoryFileProxy(f, readable)



    BINARY_MIME_TYPES = ["image/png",
                         "image/gif",
                         ]

    def dump(self, outf, no_binary=False):
        def traverse(current, path="memory:///"):
            for name, value in sorted(current.items()):
                if value.kind != NodeKind.DIR:
                    value = str(value)
                    if no_binary:
                        mt, _ = mimetypes.guess_type(name)
                        if mt in self.BINARY_MIME_TYPES:
                            hash = hashlib.md5()
                            hash.update(value)
                            value = "Binary: %s" % hash.hexdigest()
                    outf.write("--- START %s%s ---\n" % (path, name))
                    outf.write(value)
                    outf.write("\n--- END %s%s ---\n\n" % (path, name))
                else:
                    traverse(value,
                             (path[:-1] if path.endswith("/") else path) + "/" + name + "/")

        traverse(self._fs)


    def info(self, unc, set_info=None):
        current = self._get_node_for_path(self._fs, unc)
        if set_info is not None:
            if "mode" in set_info:
                current.mode = set_info["mode"]
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
        prev, current = self._get_node_prev(self._fs,
                                            [x for x in self._path(path).split("/") if x])
        if prev is not None:
            self._del_child(prev, path.last())


    def removedir(self, path):
        prev, current = self._get_node_prev(self._fs,
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
            lock = MemoryFile(self, p).lock
            assert lock.acquire(), "you tried to double-lock a file, that's currently not supported"

        if unlock is not self.SENTINEL and unlock:
            p = self._path(path)
            lock = MemoryFile(self, p).lock
            lock.release()

        if mtime is not self.SENTINEL:
            nd = self._get_node_for_path(self._fs, path)
            nd.mtime = mtime

        if next_op_callback is not self.SENTINEL:
            p = self._path(path)
            self.next_op_callbacks[p] = next_op_callback


    def supports_symlinks(self):
        return False
