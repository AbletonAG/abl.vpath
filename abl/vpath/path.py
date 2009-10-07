#******************************************************************************
# (C) 2008 Ableton AG
# Author: Stephan Diehl <stephan.diehl@ableton.com>
#******************************************************************************

"""
the abl.vpath module provides a file system abstraction layer
for local files, remote files accessed via ssh, (http, ftp) and subversion.

An URI object represents a path. It will initialized with an uri string.
For example URI('/tmp/some/dir') represents a local file '/tmp/some/dir'
and is the same as URI('file:///tmp/some/dir').
A remote file accessed via ssh could look like URI('ssh://host:/remote/path').

Additional info that can't be encoded in the uri can be given as
keyword arguments.
Example: URI('ssh://host:/path', key_filename='/local/path/to/key')

Any supported scheme has a backend.

Currently supported are:
  * file
  * svn
  * ssh
"""

from __future__ import with_statement, absolute_import

from contextlib import closing, nested
import datetime
import logging
import os
import pkg_resources
import shutil

from stat import S_ISDIR
import tempfile
import threading
import time
import traceback

from decorator import decorator

from .base import (
    URI,
    FileSystem,
    CONNECTION_REGISTRY,
    PathError,
    )




LOGGER = logging.getLogger(__name__)

#============================================================================
# Helper Classes
class Bunch(dict):
    def __setattr__(self, key, item):
        self[key] = item

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError

    def __delattr__(self, key):
        try:
            del self[key]
        except KeyError:
            raise AttributeError

    def copy(self):
        return Bunch(**super(Bunch, self).copy())

    def get_prefix(self, prefix):
        other = self.__class__()
        keys = [x for x in self.keys() if x.startswith(prefix)]
        for key in keys:
            other[key] = self[key]
        return other

class LogEntry(Bunch):
    """
    An (SVN) log entry.
    """
    def __init__(self, raw_entry):
        self.author = raw_entry.author
        self.date = datetime.datetime.fromtimestamp(raw_entry.date)
        self.message = raw_entry.message
        self.revision_number = raw_entry.revision.number
        self.changed_paths = tuple(
            [(x.action, x.path) for x in raw_entry.changed_paths]
            )

    def __hash__(self):
        return hash(tuple(self.items()))


def binsearch(value, accessor, hi, lo):
    """
    some variant of binary search:
    value: the value to compare to
    accessor: function that takes index i such that:
        lo <= i <= hi
        j < k ==> accessor(j) <= accessor(k)
    the function returns lo if value <= accessor(lo)
    and hi+1 if value > accessor(hi)

    otherwise min(i) for value <= accessor(i) is returned
    """
    mid = 0
    lowest = lo
    while lo <= hi:
        mid = (lo + hi) // 2
        val = accessor(mid)
        if val < value:
            lo = mid + 1
        elif value < val:
            hi = mid - 1
        else:
            return mid
    return lo

#============================================================================
# Exceptions

class NoSchemeError(PathError):
    "NoSchemeError is raised if scheme is used that has no backend"

class WrongSchemeError(PathError):
    "WrongSchemeError is raised if functionality requires specific schemes"

class FileDoesNotExistError(PathError):
    "FileDoesNotExistError is raised, if resource does not exist"

class NoDefinedOperationError(PathError):
    "NoDefinedOperationError is raised if method is not supported by backend"

class OptionsError(PathError):
    "OptionsError is raised if specific options need to be used"


#----------------------------------------------------------------------------

class LocalFileSystem(FileSystem):
    scheme = 'file'

    def _initialize(self):
        pass

    def open(self, unc, options=None):
        if options is not None:
            return open(self._path(unc), options)
        else:
            return open(self._path(unc))

    def listdir(self, unc, options=None):
        return os.listdir(self._path(unc))

    def removefile(self, unc):
        pth = self._path(unc)
        try:
            return os.unlink(pth)
        except WindowsError:
            import win32api
            import win32con
            win32api.SetFileAttributes(pth, win32con.FILE_ATTRIBUTE_NORMAL)
            return os.unlink(pth)

    def removedir(self, unc):
        pth = self._path(unc)
        try:
            return os.rmdir(pth)
        except WindowsError:
            import win32api
            import win32con
            win32api.SetFileAttributes(pth, win32con.FILE_ATTRIBUTE_NORMAL)
            return os.rmdir(pth)

    def mkdir(self, unc):
        path = self._path(unc)
        if path:
            return os.mkdir(path)

    def exists(self, unc):
        return os.path.exists(self._path(unc))

    def isfile(self, unc):
        return os.path.isfile(self._path(unc))

    def isdir(self, unc):
        return os.path.isdir(self._path(unc))

    def move(self, source, dest):
        if dest.scheme == 'file':
            if dest.isfile():
                dest.remove()
            elif dest.isdir():
                dest.remove('r')
            # had an os.rename here first, but that doesn't work
            # across fs boundaries on windows.
            return shutil.move(source.path, dest.path)
        else:
            return super(LocalFileSystem, self).move(source, dest)

    def copy(self, source, dest, options=None, ignore=None):

        if ignore is not None:
            ignore = set(ignore)
        else:
            ignore = set()
        if not source.exists():
            raise FileDoesNotExistError(str(source))
        if options is None:
            assert source.isfile()
            if dest.isdir():
                dest = dest / source.last()
            with nested(source.open('rb'), dest.open('wb')) as (infs, outfs):
                shutil.copyfileobj(infs, outfs, 8192)
        elif 'r' in options:
            assert source.isdir()
            if dest.exists():
                droot = dest / source.last()
            else:
                droot = dest
            droot.makedirs()
            spth = source.path
            spth_len = len(spth) + 1
            for root, dirs, files in source.walk():
                rpth = root.path
                tojoin = rpth[spth_len:].strip()
                if tojoin:
                    dbase = droot / tojoin
                else:
                    dbase = droot
                for folder in dirs[:]:
                    if folder in ignore:
                        dirs.remove(folder)
                        continue
                    ddir = dbase / folder
                    ddir.makedirs()
                for fname in files:
                    source = root / fname
                    dest = dbase / fname
                    with nested(
                        source.open('rb'),
                        dest.open('wb')
                        ) as (infs, outfs):
                        shutil.copyfileobj(infs, outfs, 8192)



#----------------------------------------------------------------------------

class TempFileHandle(object):
    """
    TempFileHandle
    --------------

    remove the (temp) file after closing the handle.
    This is used in the following situation:
    1. place some content into temp file
    2. read the content once
    """
    def __init__(self, tmpfilename):
        self.tmpfilename = tmpfilename
        self.handle = open(self.tmpfilename)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        return self.close()

    def read(self, limit=-1):
        return self.handle.read(limit)

    def close(self):
        retval = self.handle.close()
        os.unlink(self.tmpfilename)
        return retval



#----------------------------------------------------------------------------

for entrypoint in pkg_resources.iter_entry_points('abl.vpath.plugins'):
    plugin_class = entrypoint.load()
    CONNECTION_REGISTRY.register(plugin_class.scheme, plugin_class)
