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

from contextlib import nested, closing
import datetime
import logging
import os
import shutil

from stat import S_ISDIR
import tempfile
import threading
import time
import traceback

from decorator import decorator
import paramiko
import pysvn

from .base import URI, FileSystem, CONNECTION_REGISTRY




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

class PathError(Exception):
    "PathError: base exception for path module."

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

class RemoteConnectionTimeout(PathError):
    "Remote connection could not be established"


#----------------------------------------------------------------------------

class LocalFileSystem(FileSystem):

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


#----------------------------------------------------------------------------

class IgnoreMissingHostKeyPolicy(paramiko.MissingHostKeyPolicy):
    """
    IgnoreMissingHostKeyPolicy is used by SSHRemoteActions in order to
    ignore a missing host_key file. Since we are only locally active, we
    don't really care if we are talking to the right server :-)
    """

    def missing_host_key(self, client, hostname, key):
        pass


@decorator
def ssh_retry(func, self, *args, **argd):
    """
    simple ssh retry decorator to try a one shot retry in case there
    is a ChannelException.
    """
    try:
        return func(self, *args, **argd)
    except paramiko.ChannelException:
        try:
            self.close()
        except:pass
        self._initialize()
        return func(self, *args, **argd)

class SshFileSystem(FileSystem):

    def _initialize(self):
        self.client = client = paramiko.SSHClient()
        client.set_missing_host_key_policy(IgnoreMissingHostKeyPolicy())
        client.connect(
            self.hostname,
            username = self.username,
            timeout=5.0,
            **self.extras
            )
        self.sftp_client = client.open_sftp()

    def close(self):
        self.sftp_client.close()
        self.client.close()

    def open(self, unc, options=None):
        if options is not None:
            return closing(self.sftp_client.open(self._path(unc), options))
        else:
            return closing(self.sftp_client.open(self._path(unc)))

    @ssh_retry
    def listdir(self, unc, options=None):
        return self.sftp_client.listdir(self._path(unc))

    @ssh_retry
    def removefile(self, unc):
        return self.sftp_client.remove(self._path(unc))

    @ssh_retry
    def removedir(self, unc):
        return self.sftp_client.rmdir(self._path(unc))

    @ssh_retry
    def mkdir(self, unc):
        return self.sftp_client.mkdir(self._path(unc))

    @ssh_retry
    def exists(self, unc):
        try:
            self.sftp_client.stat(self._path(unc))
            return True
        except IOError:
            return False

    def isfile(self, unc):
        return self.exists(unc) and not self.isdir(unc)

    @ssh_retry
    def isdir(self, unc):
        try:
            status = self.sftp_client.stat(self._path(unc))
            return S_ISDIR(status.st_mode)
        except IOError:
            return False

    @ssh_retry
    def copy(self, source, dest, options=None, ignore=None):
        if source.scheme == 'ssh' and dest.scheme == 'file' and options is None:
            self.sftp_client.get(source.path, dest.path)
        elif (
            source.scheme == 'file' and
            dest.scheme == 'ssh' and
            options is None
            ):
            self.sftp_client.put(source.path, dest.path)
        else:
            super(SshFileSystem, self).copy(source, dest, options, ignore)


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

class SvnFileSystem(FileSystem):

    def _initialize(self):
        def svn_login_callback(realm, username, may_save):
            username = self.username
            password = self.password
            return True, username, password, True

        self.lock = threading.Lock()
        self.client = pysvn.Client()
        self.client.callback_get_login = svn_login_callback
        rn = self.extras.get('revision_number', 0)
        self.revision_number = None
        if rn:
            self.revision_number = pysvn.Revision(
                pysvn.opt_revision_kind.number,
                rn
                )

    def _checkout_or_update(self, source, dest):
        LOGGER.info('SvnFileSystem._checkout_or_update')
        LOGGER.info('SRC: %s' % source)
        LOGGER.info('DEST: %s' % dest)
        do_checkout = True
        if dest.isdir():
            LOGGER.info('try an update')
            try:
                with self.lock:
                    if self.revision_number:
                        self.client.update(
                            dest.path,
                            revision=self.revision_number
                            )
                    else:
                        self.client.update(dest.path)
                    for file_status in self.client.status(
                        dest.path,
                        recurse=True,
                        get_all=False
                        ):
                        if not file_status['is_versioned']:
                            pth = URI(file_status['path'])
                            LOGGER.debug('removing %s' % pth.path)
                            if pth.isfile():
                                pth.remove()
                            elif pth.isdir():
                                pth.remove('r')
                    do_checkout = False

            except:
                do_checkout = False
                print "================================="
                traceback.print_exc()
                print "================================="
                if dest.isdir():
                    dest.remove('r')

        if do_checkout:
            LOGGER.info('try an checkout')
            base_dir = dest.directory()
            if not base_dir.isdir():
                base_dir.makedirs()
            with self.lock:
                if self.revision_number is not None:
                    self.client.checkout(
                        source.uri,
                        dest.path,
                        revision=self.revision_number
                        )
                else:
                    self.client.checkout(source.uri, dest.path)

    def listdir(self, source, options=None):
        if not source.scheme == 'svn':
            raise WrongSchemeError("svn copy needs a svn url as first arg")
        if not source.isdir():
            raise PathError("%s must be a directory" % source.uri)
        if options == 'r':
            with self.lock:
                result = self.client.list(source.uri, recurse=True)
            result = [x[0].repos_path for x in result]
            orig = result[0]
            result = result[1:]
            rlen = len(orig) + 1
            return [x[rlen:] for x in result]
        else:
            with self.lock:
                result = self.client.list(source.uri, depth=pysvn.depth.immediates)
            # call will return info about itself as well :-(
            result = result[1:]
            result = [x[0].repos_path for x in result]
            return [x.rsplit('/',1)[1] for x in result]

    def copy(self, source, dest, options=None, **argd):
        """
        copy:  do an 'svn checkout' or 'svn update', depending on the
               existance of dest.

        TODO: think about 'svnlocal' scheme for doing operations on
              an already checked out repository. Depending on (source, dest)
              combinations, the following operations could be possible:
              (svn, file): svn export
              (svn, svn): svn cp
              (svn, svnlocal): svn co / svn update
              (svnlocal, svn): svn ci
              (svnlocal, svnlocal): merge
        """
        if not source.scheme == 'svn':
            raise WrongSchemeError("svn copy needs a svn url as first arg")
        if not dest.scheme == 'file':
            raise WrongSchemeError("svn copy needs a file url as second arg")
        if 'r' in options: # we are doing a checkout or update
            self._checkout_or_update(source, dest)
        else:
            raise OptionsError("svn copy needs the 'r' option for now")

    def move(self, source, destination):
        raise NoDefinedOperationError("SvnFileSystem does not support move")

    #def walk(self, top, topdown=True):
    #    raise NoDefinedOperationError("SvnFileSystem does not support walk")

    def exists(self, path):
        try:
            return self.info(path).kind != pysvn.node_kind.none
        except pysvn.ClientError:
            return False

    def isfile(self, path):
        try:
            return self.info(path).kind == pysvn.node_kind.file
        except pysvn.ClientError:
            return False

    def isdir(self, path):
        try:
            return self.info(path).kind == pysvn.node_kind.dir
        except pysvn.ClientError:
            return False

    def log_by_time(self, path, start_time=None, stop_time=None):
        # let's start with head
        assert start_time > stop_time
        def accessor(revision_number):
            p = URI(path.uri, revision_number=revision_number)
            return p.info.last_changed_date

        highest_revision=path.info.last_changed_revision_number
        rn_start = min(
            binsearch(start_time, accessor, highest_revision, 1),
            highest_revision
            )
        rn_end = binsearch(stop_time, accessor, highest_revision, 1)
        revision_start = pysvn.Revision(
            pysvn.opt_revision_kind.number,
            rn_start
            )
        revision_end = pysvn.Revision(
            pysvn.opt_revision_kind.number,
            rn_end
            )
        with self.lock:
            result = self.client.log(
                path.uri,
                revision_start = revision_start,
                revision_end = revision_end,
                discover_changed_paths = True
                )

        return [LogEntry(x) for x in result]

        return []

    def open(self, path, options):
        """
        we want to support reading a single file from remote repository
        as a convenience method.
        The remote file will be exported the the local filesystem.
        After closing the filehandle, the local tempfile is removed.
        """
        assert options is None or options == 'r', options
        tmp_file_name = tempfile.mktemp()
        if self.revision_number is not None:
            self.client.export(
                path.uri,
                tmp_file_name,
                recurse=False,
                revision=self.revision_number
                )
        else:
            self.client.export(
                path.uri,
                tmp_file_name,
                recurse=False
                )
        return TempFileHandle(tmp_file_name)

    def log(self, path, revision_end_number=0):
        if self.revision_number is None:
            revision_start = pysvn.Revision(
                pysvn.opt_revision_kind.head
                )
        else:
            revision_start = self.revision_number
        revision_end = pysvn.Revision(
            pysvn.opt_revision_kind.number,
            revision_end_number
            )

        with self.lock:
            result = self.client.log(
                path.uri,
                revision_start = revision_start,
                revision_end = revision_end,
                discover_changed_paths = True
                )

        return [LogEntry(x) for x in result]

    def info(self, path):
        with self.lock:
            if self.revision_number:
                info_list = self.client.info2(
                    path.uri,
                    self.revision_number,
                    recurse=False
                    )
            else:
                info_list = self.client.info2(
                    path.uri,
                    recurse=False
                    )
        if info_list:
            obj = Bunch(info_list[0][1].items())
            obj.revision_number = obj.rev.number
            del obj['rev']
            obj.last_changed_revision_number = obj.last_changed_rev.number
            del obj['last_changed_rev']
            obj.last_changed_date = datetime.datetime.fromtimestamp(
                obj.last_changed_date
                )
            return obj
        else:
            return Bunch()


class SvnLocalFileSystem(SvnFileSystem):

    def info(self, path):
        info_obj = self.client.info(path.path)
        if info_obj is not None:
            obj = Bunch(info_obj.items())
            obj.revision_number = obj.revision.number
            del obj['revision']
            obj.last_changed_revision_number = obj.commit_revision.number
            del obj['commit_revision']
            obj.last_changed_date = datetime.datetime.fromtimestamp(
                obj.commit_time
                )
            del obj['commit_time']
            return obj
        else:
            return Bunch()

    def update(self, path):
        return self.client.update(path.path)

    def copy(self, other, options='', **argd):
        raise NotImplemtedError


#----------------------------------------------------------------------------

CONNECTION_REGISTRY.register('file', LocalFileSystem)
CONNECTION_REGISTRY.register('ssh', SshFileSystem)
CONNECTION_REGISTRY.register('svn', SvnFileSystem)
CONNECTION_REGISTRY.register('svnlocal', SvnLocalFileSystem)

from .memory import MemoryFileSystem
CONNECTION_REGISTRY.register('memory', MemoryFileSystem)

