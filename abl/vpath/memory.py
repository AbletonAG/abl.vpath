from __future__ import absolute_import

from cStringIO import StringIO

from .base import FileSystem, URI


class MemoryFile(object):


    def __init__(self):
        self._data = StringIO()


    def write(self, d):
        self._data.write(d)


    def read(self, size=-1):
        return self._data.read(size)


    def seek(self, to):
        self._data.seek(to)


    def __enter__(self):
        return self


    def __exit__(self, *args):
        pass


class MemoryFileSystem(FileSystem):

    def _initialize(self):
        self._fs = {}


    def isdir(self, path):
        p = self._path(path)
        # cut off leading slash, that's our root
        assert p.startswith("/")
        p = p[1:]
        current = self._fs
        if p:
            for part in p.split("/"):
                if part in current:
                    current = current[part]
                else:
                    return False

        return True


    def mkdir(self, path):
        p = self._path(path)
        # cut off leading slash, that's our root
        assert p.startswith("/")
        p = p[1:]
        current = self._fs
        if p:
            existing_dirs = p.split("/")[:-1]
            dir_to_create = p.split("/")[-1]
            for part in existing_dirs:
                current = current[part]
            current[dir_to_create] = {}


    def open(self, path, options):
        p = self._path(path)
        # cut off leading slash, that's our root
        assert p.startswith("/")
        p = p[1:]
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


