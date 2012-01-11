from __future__ import absolute_import

import mimetypes
import hashlib
import time
import errno
import threading

from cStringIO import StringIO

from .fs import FileSystem, BaseUri, URI
from .exceptions import FileDoesNotExistError

from abl.util import Bunch, LockFileObtainException


class MemoryFile(object):

    FILE_LOCKS = {}

    def __init__(self, fs, path):
        self.path = path
        self.fs = path
        self._data = StringIO()
        self._line_reader = None
        self.mtime = self.ctime = time.time()
        self.lock = self.FILE_LOCKS.setdefault((self.fs, self.path), threading.Lock())


    def __len__(self):
        pos = self._data.tell()
        self._data.seek(-1,2)
        length = self._data.tell() + 1
        self._data.seek(pos)
        return length


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




class MemoryFileSystemUri(BaseUri):pass


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
        self._fs = {}


    def _path(self, path):
        p = super(MemoryFileSystem, self)._path(path)
        # cut off leading slash, that's our root
        assert p.startswith("/")
        p = p[1:]
        return p


    def isdir(self, path):
        p = self._path(path)
        current = self._fs
        if p:
            for part in p.split("/"):
                if part in current:
                    current = current[part]
                else:
                    return False

            return isinstance(current, dict)
        return True


    def isfile(self, path):
        p = self._path(path)
        current = self._fs
        if p:
            for part in p.split("/"):
                if part in current:
                    current = current[part]
                else:
                    return False

            return isinstance(current, MemoryFile)
        return False


    def mkdir(self, path):
        p = self._path(path)
        current = self._fs
        if p:
            existing_dirs = p.split("/")[:-1]
            dir_to_create = p.split("/")[-1]
            for part in existing_dirs:
                current = current[part]
            if dir_to_create in current:
                raise OSError(17, "File exists: %r" % str(path))
            current[dir_to_create] = {}


    def exists(self, path):
        p = self._path(path)
        current = self._fs
        if p:
            for part in p.split("/"):
                if part in current:
                    current = current[part]
                else:
                    return False
            return True
        else:
            # we are root, which always exists
            return True


    def open(self, path, options, mimetype):
        p = self._path(path)
        existing_dirs = p.split("/")[:-1]
        file_to_create = p.split("/")[-1]
        current = self._fs

        for part in existing_dirs:
            current = current[part]


        readable = False

        if options is None or "r" in options:
            f = current[file_to_create]
            f.seek(0)
            readable = True

        elif "w" in options or file_to_create not in current:
            if file_to_create in current and isinstance(current[file_to_create], dict):
                raise IOError(errno.EISDIR, "File is directory" )
            current[file_to_create] = MemoryFile(self, p)
            f = current[file_to_create]

        elif "a" in options:
            f = current[file_to_create]
            f.seek(len(f))


        return MemoryFileProxy(f, readable)



    BINARY_MIME_TYPES = ["image/png",
                         "image/gif",
                         ]

    def dump(self, outf, no_binary=False):
        def traverse(current, path="memory:///"):
            for name, value in sorted(current.items()):
                if not isinstance(value, dict):
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
                    traverse(value, (path[:-1] if path.endswith("/") else path) + "/" + name + "/")

        traverse(self._fs)


    def info(self, unc, verbosity=0):
        # TODO-dir: currently only defined
        # for file-nodes!
        p = self._path(unc)
        current = self._fs

        for part in p.split("/"):
            current = current[part]
        return Bunch(mtime=current.mtime,
                     size=len(current._data.getvalue())
                     )



    def listdir(self, path, recursive=False):
        p = self._path(path)
        current = self._fs
        for part in [x for x in p.split("/") if x]:
            current = current[part]
        return sorted(current.keys())


    def mtime(self, path):
        p = self._path(path)
        current = self._fs
        for part in p.split("/"):
            current = current[part]
        return current.mtime


    def _removeitem(self, path):
        p = self._path(path)
        current = self._fs
        prev = None
        for part in [x for x in p.split("/") if x]:
            prev = current
            current = current[part]
        if prev is not None:
            del prev[part]

    removefile = _removeitem

    removedir = _removeitem



    def lock(self, path, fail_on_lock, cleanup):
        return MemoryLock(self, path, fail_on_lock, cleanup)


    SENTINEL = object()


    def _manipulate(self, path, lock=SENTINEL, unlock=SENTINEL, mtime=SENTINEL):
        if lock is not self.SENTINEL and lock:
            p = self._path(path)
            lock = MemoryFile(self, p).lock
            assert lock.acquire(), "you tried to double-lock a file, that's currently not supported"

        if unlock is not self.SENTINEL and unlock:
            p = self._path(path)
            lock = MemoryFile(self, p).lock
            lock.release()


        if mtime is not self.SENTINEL:
            p = self._path(path)
            current = self._fs
            for part in p.split("/"):
                current = current[part]
            current.mtime = mtime
