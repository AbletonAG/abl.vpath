#******************************************************************************
# (C) 2008 Ableton AG
# Author: Stephan Diehl <stephan.diehl@ableton.com>
#******************************************************************************
from __future__ import with_statement, absolute_import

import datetime
import logging
import os
import platform
import shutil
import stat
import subprocess

from .fs import FileSystem, BaseUri, denormalize_path
from .exceptions import FileDoesNotExistError

from abl.util import Bunch, LockFile

# check for WindowsError
try:
    raise WindowsError()
except NameError:
    WindowsError = None
except:
    pass

if platform.system() == 'Windows':
    import pywintypes
    pywinerror = pywintypes.error
else:
    pywinerror = None


LOGGER = logging.getLogger(__name__)
#----------------------------------------------------------------------------

class LocalFileSystemUri(BaseUri):
    def __str__(self):
        return self.path

    @property
    def path(self):
        path = self.parse_result.path
        if self.sep != '/':
            return denormalize_path(path, self.sep)
        else:
            return super(LocalFileSystemUri, self).path

class LocalFileSystem(FileSystem):
    scheme = 'file'
    uri = LocalFileSystemUri

    def _initialize(self):
        pass

    def info(self, unc, verbosity=0):
        p = self._path(unc)
        stats = os.stat(p)
        ctime = stats[stat.ST_CTIME]
        mtime = stats[stat.ST_MTIME]
        atime = stats[stat.ST_ATIME]
        size = stats[stat.ST_SIZE]
        mode = stats[stat.ST_MODE]
        return Bunch(
            ctime = datetime.datetime.fromtimestamp(ctime),
            mtime = datetime.datetime.fromtimestamp(mtime),
            atime = datetime.datetime.fromtimestamp(atime),
            size = size,
            mode = mode,
            )

    def open(self, unc, options=None, mimetype='application/octet-stream'):
        if options is not None:
            return open(self._path(unc), options)
        else:
            return open(self._path(unc))

    def listdir(self, unc, recursive=False):
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

    def rmtree(self, unc):
        pth = self._path(unc)
        try:
            return shutil.rmtree(pth)
        except (WindowsError, pywinerror), exp:
            subprocess.call(['cmd','/C', 'rmdir', '/Q', '/S', pth])

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
        """
        the semantic should be like unix 'mv' command.
        Unfortunatelly, shutil.move does work differently!!!
        Consider (all paths point to directories)
        mv /a/b /a/c
        expected outcome:
        case 1.: 'c' does not exist:
          b moved over to /a such that /a/c is what was /a/b/ before
        case 2.: 'c' does exist:
          b is moved into '/a/c/' such that we have now '/a/c/b'

        But shutil.move will use os.rename whenever possible which means that
        '/a/b' is renamed to '/a/c'. The outcome is that the content from b
        ends up in c.
        """
        if dest.scheme == 'file':
            if source.isdir() and dest.isdir():
                dest /= source.basename()
            return shutil.move(source.path, dest.path)
        else:
            return super(LocalFileSystem, self).move(source, dest)


    def lock(self, path, fail_on_lock, cleanup):
        return LockFile(str(path), fail_on_lock=fail_on_lock, cleanup=cleanup)


    def mtime(self, path):
        return self.info(path).mtime

