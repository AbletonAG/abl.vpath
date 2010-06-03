from __future__ import absolute_import

import mimetypes
import hashlib
import time

from cStringIO import StringIO

from .fs import FileSystem, BaseUri, URI
from .misc import Bunch


class MemoryFile(object):


    def __init__(self):
        self._data = StringIO()
        self.mtime = self.ctime = time.time()


    def write(self, d):
        self._data.write(d)
        self.mtime = time.time()


    def read(self, size=-1):
        return self._data.read(size)


    def seek(self, to):
        self._data.seek(to)


    def __enter__(self):
        return self


    def __exit__(self, *args):
        pass


    def __str__(self):
        return self._data.getvalue()

class MemoryFileSystemUri(BaseUri):pass

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


    def open(self, path, options):
        p = self._path(path)
        existing_dirs = p.split("/")[:-1]
        file_to_create = p.split("/")[-1]
        current = self._fs

        for part in existing_dirs:
            current = current[part]

        if options is None or "r" in options:
            f = current[file_to_create]
            f.seek(0)
            return f

        if "w" in options or file_to_create not in current:
            current[file_to_create] = MemoryFile()
            return current[file_to_create]
        if "a" in options:
            f = current[file_to_create]
            f.seek(len(f))
            return f

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


    def info(self, unc):
        # TODO-dir: currently only defined
        # for file-nodes!
        p = self._path(unc)
        current = self._fs

        for part in p.split("/"):
            current = current[part]
        return Bunch(mtime=current.mtime)

    def listdir(self, path, options=None):
        p = self._path(path)
        current = self._fs
        for part in p.split("/"):
            current = current[part]
        return sorted(current.keys())
