import atexit
from collections import defaultdict
import fnmatch
import hashlib
import os
import stat
import re
import shutil
import threading
import time
import traceback

from decorator import decorator
import pkg_resources

from .simpleuri import UriParse, uri_from_parts
from .exceptions import (NoSchemeError,
                         FileDoesNotExistError,
                         OperationIsNotSupportedOnPlatform)


class ConnectionRegistry(object):
    """
    ConnectionRegistry: Singleton for file system backend registry

    Not ready for multithreaded code yet!!!

    Any backend must register itself (or must be registered).
    The URI object will ask the registry for the backend to use.

    @type connections: dict
    @ivar connections: holds all open connections

    @type schemes: dict
    @ivar schemes: key is a scheme;
                   value is a factory function for scheme's backend

    @type run_clean_tread: bool
    @ivar run_clean_thread: boolean indicating if the cleaner thread
                            should run, or not (shut down)

    @type clean_interval: int
    @ivar clean_interval: run the cleaning session every
                          <clean_interval> seconds
    @type clean_timeout: int
    @ivar clean_timeout: close an open backend session after
                         <clean_timeout> seconds and remove
                         it.
    @type cleaner_thread: threading.Thread
    @ivar cleaner_thread: thread do run the cleaner method.

    @type creation_queue: Queue.Queue
    @ivar creation_queue: queue for creating connections

    @type creation_thread: threading.Thread
    @ivar creation_thread: paramiko is not setting its connection threads
                           into daemonic mode. Due to this, it might be
                           difficult to shut down a program, using paramiko if
                           there is still an open connection. Since the i
                           daemonic flag is inherited from the parent, the
                           construction here makes sure that such connections
                           are only created within a daemonic thread.
    """

    def __init__(self, clean_interval=300, clean_timeout=1800):
        self.connections = {}
        self.schemes = {}
        self.run_clean_thread = True
        self.clean_interval = clean_interval
        self.clean_timeout = clean_timeout
        self.cleaner_thread = threading.Thread(target=self.cleaner)
        self.cleaner_thread.setDaemon(True)
        self.cleaner_thread.start()
        self.creation_locks = defaultdict(threading.Lock)


    def create(self, scheme, key, extras):
        with self.creation_locks[scheme]:
            conn = self.schemes[scheme](*key[1:-1], **extras)
            self.connections[key] = conn


    def get_connection(self,
        scheme='',
        hostname=None,
        port=None,
        username=None,
        password=None,
        vpath_connector=None,
        **extras
        ):
        """
        get_connection: get connection for 'scheme' or create a new one.

        @type scheme: str
        @param scheme: the scheme to use (i.e. 'file', 'ssh', etc.)

        @type hostname: str|None
        @param hostname: the hostname (extracted from parsed uri)

        @type port: str|None
        @param port: the port (extracted from parsed uri)

        @type username: str|None
        @param username: the username (extracted from parsed uri)

        @type password: str|None
        @param password: the password (extracted from parsed uri)

        @type extras: dict
        @param extras: parameters that are given to the backend factory

        A key is calculated from given parameters. This key is used
        to check for existing connection.
        """
        if scheme not in self.schemes:
            raise NoSchemeError(
                'There is no handler registered for "{}" (available: {})'.format(scheme, list(self.schemes.keys()))
                )
        key = (
            scheme,
            hostname,
            port,
            username,
            password,
            vpath_connector,
            frozenset(extras.items())
            )

        if not key in self.connections:
            self.create(scheme, key, extras)
        return self.connections[key]


    def cleanup(self, force=False):
        now = time.time()
        for key, conn in list(self.connections.items()):
            if ((now - conn.last_used) > self.clean_timeout) or force:
                try:
                    conn.close()
                except:
                    print("### Exception while closing connection %s" % conn)
                    traceback.print_exc()
                del self.connections[key]


    def cleaner(self):
        """
        cleaner: method to be run in a thread to check for stale connections.
        """
        while True:
            self.cleanup()
            now = time.time()
            try:
                while (time.time() - now) < self.clean_interval:
                    if not self.run_clean_thread:
                        return
                    time.sleep(1)
            except:
                return


    def register(self, scheme, factory):
        "register: register factory callable 'factory' with scheme"

        self.schemes[scheme] = factory


    def shutdown(self):
        """
        shutdown: to be run by atexit handler. All open connection are closed.
        """
        self.run_clean_thread = False
        self.cleanup(True)
        if self.cleaner_thread.is_alive():
            self.cleaner_thread.join()


CONNECTION_REGISTRY = ConnectionRegistry()
SCHEME_REGISTRY = {}

atexit.register(CONNECTION_REGISTRY.shutdown)

def normalize_uri(uri, sep='/'):
    if sep != '/':
        uri = uri.replace(sep, '/')
        if len(uri) > 1 and uri[1] == ':':
            uri = '/'+uri[0]+uri[2:]
    return uri


def denormalize_path(path, sep='\\'):
    if len(path) > 2 and path[0] == path[2] == '/':
        return path[1]+':'+sep+path[3:].replace('/', sep)
    else:
        return path.replace('/', sep)


def remove_dir_recursively(connection, path):
    for root, dirs, files in connection.walk(path, topdown=False,
                                             followlinks=False):
        for fname in files:
            connection.removefile(root / fname)

        for dname in dirs:
            d = root / dname
            if connection.islink(d):
                connection.removefile(d)
            else:
                connection.removedir(d)

    if connection.islink(path):
        return connection.removefile(path)
    else:
        return connection.removedir(path)


#============================================================================

@decorator
def with_connection(func, self, *args, **argd):
    """
    with_connection: decorator; make sure that there is a connection available
    for action. Set the connections 'last_used' attribute to current timestamp.
    We always get a fresh connection from the CONNECTION REGISTRY since the
    'extras' could have changed.
    """
    self.connection = self.get_connection()
    self.connection.last_used = time.time()
    self.connection.pre_call_hook(self, func)
    return func(self, *args, **argd)


#============================================================================

scheme_re = re.compile("([a-z+-]+)://")

def URI(uri, sep=os.sep, **extras):
    scheme = 'file'
    if isinstance(uri, BaseUri):
        scheme = uri.scheme
    else:
        m = scheme_re.match(uri)
        if m is not None:
            scheme = m.group(1)

    return SCHEME_REGISTRY.get(scheme, BaseUri)(
        uri,
        sep=sep,
        **extras
        )


class BaseUri(object):
    """An URI object represents a path, either on the local filesystem or on a
    remote server. On creation, the path is represented by an (more or less
    conform) uri like 'file:///some/local/file' or 'ssh://server:/remote/file'.

    The well kwown 'os'/'os.path' interface is used.

    Internally, the path separator is always '/'. The path property will
    return the url with the path separator that is given with 'sep'
    which defaults to 'os.sep'.

    The 'join' (as in os.path.join) can be used with the operator '/' which
    leads to more readable code.
    """

    def __init__(self, uri, sep=os.sep, **extras):
        self._scheme = ''
        self.connection = None
        if isinstance(uri, BaseUri):
            self.uri = uri.uri
            self.sep = uri.sep
            self.parse_result = UriParse(uri.uri)
            self.extras = uri.extras.copy()
        else:
            if uri.startswith('file://'):
                uri = uri[7:]
            uri = normalize_uri(uri, '\\')
            if not '://' in uri and not (uri.startswith('/') or uri.startswith('.')):
                uri = './'+uri
            if not '://' in uri:
                uri = 'file://'+uri
            self.uri = uri
            self.sep = sep
            self.parse_result = UriParse(uri)
            self.extras = extras
        if self.username is None:
            if 'username' in self.extras:
                self.username = self.extras.pop('username')
            elif 'username' in self.parse_result.query:
                self.username = self.parse_result.query['username']
        if self.password is None:
            if 'password' in self.extras:
                self.password = self.extras.pop('password')
            elif 'password' in self.parse_result.query:
                self.password = self.parse_result.query['password']


    def get_connection(self):
        return CONNECTION_REGISTRY.get_connection(*self._key(), **self._extras())


    def _extras(self):
        extras = self.extras.copy()
        if self.scheme not in ('http','https'):
            extras.update(self.query)

        return extras


    def _get_scheme(self):
        if not self._scheme:
            scheme = self.parse_result.scheme
            self._scheme = scheme
        return self._scheme


    def _set_scheme(self, scheme):
        self._scheme = scheme
        self.parse_result.scheme = scheme


    scheme = property(_get_scheme, _set_scheme)

    @property
    def port(self):
        try:
            return self.parse_result.port
        except ValueError:
            return None


    @property
    def path(self):
        path = self.parse_result.path
        if path.startswith('/.'):
            return path[1:]
        else:
            return path


    @property
    def unipath(self):
        pathstr = self.parse_result.path
        if not (pathstr.startswith('.') or pathstr.startswith('/')):
            return './'+pathstr
        else:
            return pathstr


    def _key(self):
        return (
            self.scheme,
            self.hostname,
            self.port,
            self.username,
            self.password,
            self.vpath_connector,
            )


    def __str__(self):
        return str(self.parse_result)


    def __repr__(self):
        return str(self)


    def __getattr__(self, attr):
        return getattr(self.parse_result, attr)


    def __eq__(self, other):
        if isinstance(other, BaseUri):
            return self.parse_result == other.parse_result
        else:
            return False


    def __ne__(self, other):
        return not self == other


    def __div__(self, other):
        return self.join(other)


    def __truediv__(self, other):
        return self.join(other)


    def __add__(self, suffix):
        path = self.uri + suffix
        result = self.__class__(
            path,
            sep=self.sep,
            **self._extras()
            )
        result.parse_result.query = self.query.copy()
        return result


    @property
    def is_absolute(self):
        path = self.parse_result.path
        if path.startswith('/.'):
            path = path[1:]
        return path.startswith('/')


    def split(self):
        """
        split: like os.path.split

        @rtype: tuple(URI, str)
        @return: a 2 tuple. The first element is a URI instance and the second
                 a string, representing the basename.
        """
        try:
            first, second = self.uri.rsplit('/', 1)
        except ValueError:
            first = ''
            second = self.uri
        # we might be already on the root
        if first.endswith('//'):
            first = first + '/'
        if not first:
            first = '.'
        return (self.__class__(
            first,
            sep=self.sep,
            **self._extras()
            ),
            second.partition('?')[0]
            )


    def directory(self, level=1):
        """
        @return: the first part of the split method
        """
        assert level > 0
        newpath = self
        while level>0:
            newpath = newpath.split()[0]
            level -= 1
        return newpath


    # os.path-compliance
    dirname = directory

    def basename(self):
        """
        @return: the second part of the split method
        """
        return self.split()[1]


    def splitext(self):
        return os.path.splitext(self.basename())


    def last(self):
        """
        last: similar to 'basename', but makes sure that the last part is
              really returned.
              example: URI('/some/dir/').basename() will return '' while
                       URI('/some/dir/').last() will return 'dir'.

        @return: last part of uri
        @rvalue: str
        """
        parts = self.uri.split('/')
        if not parts:
            return ''
        if len(parts) > 1:
            if not parts[-1]:
                return parts[-2]
            else:
                return parts[-1]
        else:
            return parts[-1]


    def join(self, *args):
        """
        join: join paths parts together to represent a path.

        @return: URI instance of joined path
        @rtype: URI
        """
        sep = self.sep
        if sep != '/':
            args = [x.replace(sep, '/') for x in args]
        args = (
            [self.parse_result.path.rstrip('/')] +
            [x.strip('/') for x in args[:-1]] +
            [args[-1]]
            )
        parts = self.parse_result.as_list()
        parts[2] = '/'.join(args)

        result = self.__class__(
            uri_from_parts(parts),
            sep=sep,
            **self._extras()
            )

        result.parse_result.query = self.query.copy()

        return result


    @with_connection
    def copy(self, other, recursive=False, ignore=None,
             followlinks=True):
        """
        copy: copy self to other

        @type other: URI
        @param other: the path to copy itself over.

        What will really happen depends on the backend.

        Note that file properties are only copied when self and other are
        located in the same backend, i.e. it is not possible to copy
        permissions etc. from a memory:// to a file:// based path.
        """
        return self.connection.copy(self, other,
                                    recursive=recursive,
                                    ignore=ignore,
                                    followlinks=followlinks)


    @with_connection
    def copystat(self, other):
        """
        copystat: copy file/folder metadata from self to other

        @type other: URI
        @param other: the path to copy the metadata to.

        Will copy file permissions, mtime, atime, etc. to path. Note:
        this ALWAYS follows symlinks. Consider using info with
        followslinks set to False to read and write the stat info of a
        symlink.
        """
        return self.connection.copystat(self, other)


    @with_connection
    def move(self, other):
        """
        move: move self to other

        @type other: URI
        @param other: the path to copy itself over.

        What will really happen depends on the backend.
        """
        return self.connection.move(self, other)


    @with_connection
    def remove(self, recursive=False):
        """
        remove: shortcut method to remove self.
        if 'self' represents a file, the backends 'removefile' method id used.
        if 'self' represents a directory, it will recursivly removed, if
        the options string contains 'r'. Otherwise, the backends 'removedir'
        method is used.
        """
        if self.connection.islink(self):
            return self.connection.removefile(self)

        if not self.connection.exists(self):
            raise FileDoesNotExistError(str(self))

        if self.connection.isdir(self):
            if recursive:
                return remove_dir_recursively(self.connection, self)
            else:
                return self.connection.removedir(self)
        elif self.connection.isfile(self):
            return self.connection.removefile(self)


    @with_connection
    def open(self, options=None, mimetype='application/octet-stream'):
        """
        open: return a file like object for self.
        The method can be used with the 'with' statment.
        """
        return self.connection.open(self, options, mimetype)


    @with_connection
    def makedirs(self):
        """
        makedirs: recursivly create directory if it doesn't exist yet.
        """
        return self.connection.makedirs(self)


    @with_connection
    def mkdir(self):
        """
        mkdir: create directory self. The semantic will be the same than
        os.mkdir.
        """
        return self.connection.mkdir(self)


    @with_connection
    def exists(self):
        """
        exists:

        @rtype: bool
        @return: True is path exists on target system, else False
        """
        return self.connection.exists(self)


    @with_connection
    def isfile(self):
        """
        isfile:

        @rtype: bool
        @return: True is path is a file on target system, else False
        """
        return self.connection.isfile(self)


    @with_connection
    def isdir(self):
        """
        isdir:

        @rtype: bool
        @return: True is path is a directory on target system, else False
        """
        return self.connection.isdir(self)


    @with_connection
    def isexec(self, mode=stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH):
        """
        isexec:

        @rtype: bool
        @return: Indicates whether the path points to a file or folder
        which has the executable flag set.

        Note that on systems which do not support executables flags the
        result may be unpredicatable.  On Windows the value is determined
        by the file extension, a *.exe file is executable, a *.sh not.
        """
        return self.connection.isexec(self, mode)


    @with_connection
    def set_exec(self, mode):
        """
        set_exec:

        @rtype: void
        @return: Set the executable flag of the receiver to mode (which can
        be any combination of stat.IXUSR, stat.IXGRP, or stat.IXOTH).

        Note that on systems which do not support executables flags the
        function may have no effect.
        """
        return self.connection.set_exec(self, mode)


    @with_connection
    def islink(self):
        """
        islink:

        @rtype: bool
        @return: Indicates whether the file this path is pointing to is a
        symlink.

        On systems which don't support symlinks this return alsways False.
        """
        return self.connection.islink(self)


    @with_connection
    def readlink(self):
        """
        readlink:

        @rtype: URI
        @return: the content of the symlink this path is pointing to.
        Throws an exception if this path is not a symlink (check with
        islink before)

        On systems which don't support symlinks this will always throw.
        """
        return self.connection.readlink(self)


    @with_connection
    def symlink(self, link_name):
        """
        symlink:

        @rtype: void

        Creates a symbolic link named link_name to the file this path is
        pointing to.

        On systems which don't support symlinks this will throw.
        """
        return self.connection.symlink(self, link_name)


    @with_connection
    def mtime(self):
        """
        mtime:

        @rtype: float
        @return: the last time of modification is seconds since the epoch.
        """
        return self.connection.mtime(self)


    @with_connection
    def walk(self, topdown=True, followlinks=True):
        """
        walk: walk the filesystem (just like os.walk).
        Use like:

        path = URI('/some/dir')
        for root, dirs, files in path.walk():
            do_something()

        root will be an URI object.
        """
        return self.connection.walk(self, topdown=topdown, followlinks=followlinks)


    @with_connection
    def listdir(self):
        """
        listdir: list contents of directory self.
        The pathpart of 'self' will not be returned.
        """
        return self.connection.listdir(self)


    @with_connection
    def info(self, set_info=None, followlinks=True):
        """
        info: backend info about self (probably not implemented for
              all backends. The result will be backend specific).

        @param set_info: If not None, this data will be set on self.
        @param followlinks: If True, symlinks will be followed. If
            False, the info of the symlink itself will be returned.
            (Default: True)
        @rtype: Bunch
        @return: backend specific information about self.
        """
        return self.connection.info(self, set_info=set_info, followlinks=followlinks)


    @with_connection
    def sync(self, other, options=''):
        return self.connection.sync(self, other, options)


    @with_connection
    def glob(self, pattern):
        return self.connection.glob(self, pattern)


    @with_connection
    def md5(self):
        """
        Returns the md5-sum of this file. This is of course potentially
        expensive!
        """
        hash_ = hashlib.md5()
        with self.open("rb") as inf:
            block = inf.read(4096)
            while block:
                hash_.update(block)
                block = inf.read(4096)

        return hash_.hexdigest()


    @with_connection
    def lock(self, fail_on_lock=False, cleanup=False):
        """
        Allows to lock a file via abl.util.LockFile, with the
        same parameters there.

        Returns an opened, writable file.
        """
        return self.connection.lock(self, fail_on_lock, cleanup)


    @with_connection
    def _manipulate(self, *args, **kwargs):
        """
        This is a semi-private method. It's current use is to
        manipulate memory file system objects so that
        you can create certain conditions, to provoke
        errors that otherwise won't occur.
        """
        self.connection._manipulate(self, *args, **kwargs)



class RevisionedUri(BaseUri):
    @with_connection
    def switch(self, branch):
        return self.connection.switch(self, branch)


    @with_connection
    def update(self, recursive=True, clean=False):
        return self.connection.update(self, recursive, clean)


    @with_connection
    def log(self, limit=0, **kwargs):
        return self.connection.log(self, limit, **kwargs)


    @with_connection
    def log_by_time(self, start_time=None, stop_time=None):
        return self.connection.log_by_time(self, start_time, stop_time)



class FileSystem(object):
    """
    FileSystem is the base class for any file system.

    Some default implementations are provided for some higher functions like
    copy, makedirs, etc.
    """

    scheme = None

    def __init__(self,
                 hostname=None,
                 port=None,
                 username=None,
                 password=None,
                 vpath_connector=None,
                 **extras):
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        self.vpath_connector = vpath_connector
        self.extras = extras
        self.last_used = time.time()

        self._initialize()


    def close(self):
        pass


    def _path(self, uriobj):
        if isinstance(uriobj, BaseUri):
            return uriobj.path
        else:
            return uriobj


    def pre_call_hook(self, path, func):
        """
        Invoked for all @with_connection decorated
        functions before they get executed.
        """
        pass


    def _copy_link(self, source, dest):
        assert self.islink(source)
        if dest.isfile():
            self.removefile(dest)
        self.symlink(self.readlink(source), dest)


    def copy(self, source, dest, recursive=False, ignore=None,
             followlinks=True):
        if source.connection is dest.connection and hasattr(self, 'internal_copy'):
            return self.internal_copy(source, dest, recursive, ignore)

        use_same_backend = source.scheme == dest.scheme

        if ignore is not None:
            ignore = set(ignore)
        else:
            ignore = set()

        if not source.exists():
            raise FileDoesNotExistError(str(source))

        if not recursive:
            assert source.isfile()
            if dest.isdir():
                dest = dest / source.last()

            if source.islink() and not followlinks:
                self._copy_link(source, dest)
            else:
                with source.open('rb') as infs, dest.open('wb') as outfs:
                    shutil.copyfileobj(infs, outfs, 8192)
                if use_same_backend:
                    self.copystat(source, dest)
        else:
            assert source.isdir()
            if dest.isdir():
                droot = dest / source.last()
            else:
                droot = dest

            if source.islink() and not followlinks:
                self._copy_link(source, droot)
            else:
                droot.makedirs()
                spth = source.path
                spth_len = len(spth) + 1
                for root, dirs, files in source.walk(followlinks=followlinks):
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
                        srcp = root / folder
                        if srcp.islink() and not followlinks:
                            self._copy_link(srcp, ddir)
                        else:
                            ddir.makedirs()

                    for fname in files:
                        srcf = root / fname
                        destf = dbase / fname
                        if srcf.islink() and not followlinks:
                            self._copy_link(srcf, destf)
                        else:
                            with srcf.open('rb') as infs, destf.open('wb') as outfs:
                                shutil.copyfileobj(infs, outfs, 8192)
                            if use_same_backend:
                                self.copystat(srcf, destf)


    def makedirs(self, path):
        if path.isdir():
            return path
        pth, tail = path.split()
        if not pth.isdir():
            self.makedirs(pth)
        if tail:
            return path.mkdir()
        else:
            return path


    def move(self, source, destination):
        """
        the semantic should be like unix 'mv' command
        """
        if source.isfile():
            source.copy(destination)
            source.remove()
        else:
            source.copy(destination, recursive=True)
            source.remove('r')


    def walk(self, top, topdown=True, followlinks=True):
        names = sorted(self.listdir(top))

        dirs = []
        nondirs = []
        for name in names:
            if self.isdir(top / name):
                dirs.append(name)
            else:
                nondirs.append(name)

        if topdown:
            yield top, dirs, nondirs
        for name in dirs:
            path = top / name
            if not path.islink() or followlinks:
                for x in self.walk(path, topdown=topdown, followlinks=followlinks):
                    yield x
        if not topdown:
            yield top, dirs, nondirs


    def glob(self, path, pattern):
        # TODO-std: is this working with separators?
        res = []
        for f in path.listdir():
            if fnmatch.fnmatch(f, pattern):
                res.append(path / f)
        return res


    def _initialize(self):
        raise NotImplementedError

    def open(self, path, options, mimetype):
        raise NotImplementedError

    def listdir(self, path):
        raise NotImplementedError

    def removefile(self, path):
        raise NotImplementedError

    def removedir(self, path):
        raise NotImplementedError

    def mkdir(self, path):
        raise NotImplementedError

    def exists(self, path):
        raise NotImplementedError

    def isfile(self, path):
        raise NotImplementedError

    def isdir(self, path):
        raise NotImplementedError

    def isexec(self, path, mode):
        raise NotImplementedError

    def set_exec(self, path, mode):
        raise NotImplementedError


    def supports_symlinks(self):
        raise NotImplementedError


    def islink(self, path):
        if not self.supports_symlinks():
            return False
        raise NotImplementedError


    def readlink(self, path):
        if not self.supports_symlinks():
            raise OperationIsNotSupportedOnPlatform
        raise NotImplementedError


    def symlink(self, target, link_name):
        if not self.supports_symlinks():
            raise OperationIsNotSupportedOnPlatform
        raise NotImplementedError


    def info(self,  path, set_info=None, followlinks=True):
        raise NotImplementedError


    def sync(self, source, dest, options):
        raise NotImplementedError


    def mtime(self, path):
        raise NotImplementedError


    def copystat(self, path, other):
        raise NotImplementedError


class RevisionedFileSystem(FileSystem):
    def switch(self, revision):
        raise NotImplementedError


    def update(self, path, recursive=False, clean=False):
        raise NotImplementedError


    def log(self, path, limit=0):
        raise NotImplementedError


    def log_by_time(self, path, start_time=None, stop_time=None):
        raise NotImplementedError


for entrypoint in pkg_resources.iter_entry_points('abl.vpath.plugins'):
    try:
        plugin_class = entrypoint.load()
    except Exception as exp:
        print("Could not load entrypoint", entrypoint)
        traceback.print_exc()
        continue
    CONNECTION_REGISTRY.register(plugin_class.scheme, plugin_class)
    SCHEME_REGISTRY[plugin_class.scheme] = plugin_class.uri
