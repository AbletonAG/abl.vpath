#******************************************************************************
# (C) 2008 Ableton AG
# Author: Stephan Diehl <stephan.diehl@ableton.com>
#******************************************************************************
from __future__ import with_statement, absolute_import

from contextlib import nested
import logging
import os
import shutil

from .base import FileSystem

LOGGER = logging.getLogger(__name__)
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
