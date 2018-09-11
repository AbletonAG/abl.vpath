#******************************************************************************
# (C) 2008 Ableton AG
# Author: Stephan Diehl <stephan.diehl@ableton.com>
#******************************************************************************

import datetime
import logging
import os
import shutil
import stat
import sys

from functools import partial

from .fs import FileSystem, BaseUri, denormalize_path, URI
from .exceptions import OperationIsNotSupportedOnPlatform

from abl.util import Bunch, LockFile


LOGGER = logging.getLogger(__name__)


def lchmod(filename, mode):
    if sys.version_info[0] >= 3:
        return os.chmod(filename, mode, follow_symlinks=True)
    else:
        return os.lchmod(filename, mode)


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


    def info(self, unc, set_info=None, followlinks=True):
        p = self._path(unc)

        use_link_functions = self.islink(unc) and not followlinks
        stat_func = os.lstat if use_link_functions else os.stat
        chmod_func = lchmod if use_link_functions else os.chmod

        if set_info is not None:
            if "mode" in set_info:
                chmod_func(p, set_info["mode"])
            return

        stats = stat_func(p)
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

    def listdir(self, unc):
        return sorted(os.listdir(self._path(unc)))


    def removefile(self, unc):
        pth = self._path(unc)
        if sys.platform == 'win32':
            os.chmod(pth, stat.S_IWUSR)
        return os.unlink(pth)


    def removedir(self, unc):
        assert not unc.islink()
        pth = self._path(unc)
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


    def isexec(self, unc, mode_mask):
        return self.info(unc).mode & mode_mask != 0


    def set_exec(self, unc, mode):
        mask = stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        new_mode = (self.info(unc).mode & ~mask) | mode
        self.info(unc, dict(mode=new_mode))


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


    def copystat(self, source, dest):
        shutil.copystat(source.path, dest.path)


    def supports_symlinks(self):
        return sys.platform != 'win32'


    def islink(self, path):
        return self.supports_symlinks() and os.path.islink(self._path(path))


    def readlink(self, path):
        if not self.supports_symlinks():
            raise OperationIsNotSupportedOnPlatform
        return URI(os.readlink(self._path(path)))


    def symlink(self, target, link_name):
        if not self.supports_symlinks():
            raise OperationIsNotSupportedOnPlatform
        return os.symlink(self._path(target), self._path(link_name))

    def dump(self, outf, no_binary=False):
        pass
