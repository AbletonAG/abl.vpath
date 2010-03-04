from __future__ import with_statement


import atexit
import fnmatch
import os
import hashlib


from Queue import Queue
import threading
import time
import traceback

from decorator import decorator
import pkg_resources

from .simpleuri import UriParse, uri_from_parts
from .exceptions import NoSchemeError, RemoteConnectionTimeout


#============================================================================

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
        self.creation_queue = Queue()
        self.creation_thread = threading.Thread(target=self.create)
        self.creation_thread.setDaemon(True)
        self.creation_thread.start()

    def create(self):
        while True:
            scheme, key, extras = self.creation_queue.get()
            conn = self.schemes[scheme](*key[1:-1], **extras)
            self.connections[key] = conn

    def get_connection(self,
        scheme='',
        hostname=None,
        port=None,
        username=None,
        password=None,
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
                'There is no handler registered for "%s"' % scheme
                )
        key = (
            scheme,
            hostname,
            port,
            username,
            password,
            frozenset(extras.items())
            )

        if not key in self.connections:
            t0 = time.time()
            self.creation_queue.put((scheme, key, extras))
            while not key in self.connections:
                time.sleep(.001)
                if (time.time() - t0) > 5.0:
                    raise RemoteConnectionTimeout()
        return self.connections[key]

    def cleanup(self, force=False):
        now = time.time()
        for key, conn in self.connections.items():
            if ((now - conn.last_used) > self.clean_timeout) or force:
                try:
                    conn.close()
                except:
                    print "### Exception while closing connection %s" % conn
                    traceback.print_exc()
                del self.connections[key]

    def cleaner(self):
        """
        cleaner: method to be run in a thread to check for stale connections.
        """
        while True:
            self.cleanup()
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
        if self.cleaner_thread.isAlive():
            self.cleaner_thread.join()

CONNECTION_REGISTRY = ConnectionRegistry()

atexit.register(CONNECTION_REGISTRY.shutdown)

def normalize_uri(uri, sep='/'):
    if sep != '/':
        uri = uri.replace(sep, '/')
        if len(uri) > 1 and uri[1] == ':':
            uri = '/'+uri[0]+uri[2:]
    return uri


#============================================================================

@decorator
def with_connection(func, self, *args, **argd):
    """
    with_connection: decorator; make sure that there is a connection available
    for action. Set the connections 'last_used' attribute to current timestamp.
    """
    if self.connection is None:
        self.connection = CONNECTION_REGISTRY.get_connection(
            *self._key(),
            **self.extras
            )
    self.connection.last_used = time.time()
    try:
        return func(self, *args, **argd)
    except BaseException, exp:
        print "Got Exception:", exp
        print "Connection:", self.connection
        raise


#============================================================================

class URI(object):
    """
    An URI object represents a path, either on the local filesystem or on a
    remote server. On creation, the path is represented by an (more or less
    conform) uri like 'file:///some/local/file' or 'ssh://server:/remote/file'.

    The well kwown 'os'/'os.path' interface is used.

    Internally, the path separator is always '/'. The path property will
    return the url with the path separator that is given with 'sep'
    which defaults to 'os.sep'.

    The 'join' (as in os.path.join) can be used with the operator '/' which
    leads to more readable code.
    """

    def __init__(self, uri, sep=os.sep, connection=None, **extras):
        self._scheme = ''
        if isinstance(uri, URI):
            self.uri = uri.uri
            self.sep = uri.sep
            self.parse_result = uri.parse_result
            self.connection = uri.connection
            self.extras = uri.extras
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
            self.connection = connection
            self.extras = extras
        if self.scheme not in ('http','https'):
            # for non http schemes, the query part might contain extra
            # args for the path constructor
            self.extras.update(self.query)

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
        if self.scheme in ('file', 'svnlocal') and self.sep != '/':
            if len(path) > 2 and path[0] == path[2] == '/':
                return path[1]+':'+self.sep+path[3:].replace('/', self.sep)
            else:
                return path.replace('/', self.sep)
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
            self.password
            )

    def __str__(self):
        if self.scheme in ('file', 'svnlocal'):
            return self.path
        else:
            #return self.uri
            return str(self.parse_result)


    def __repr__(self):
        return str(self)


    def __getattr__(self, attr):
        return getattr(self.parse_result, attr)

    def __eq__(self, other):
        if isinstance(other, URI):
            return self.parse_result == other.parse_result
        else:
            return False

    def __div__(self, other):
        return self.join(other)


    def __add__(self, suffix):
        path = self.uri + suffix
        result = self.__class__(
            path,
            sep=self.sep,
            connection=self.connection,
            **self.extras
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
        if not first:
            first = '.'
        return (self.__class__(
            first,
            sep=self.sep,
            connection=self.connection,
            **self.extras
            ),
            second.partition('?')[0]
            )

    def directory(self):
        """
        @return: the first part of the split method
        """
        return self.split()[0]


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
            connection=self.connection,
            **self.extras
            )

        result.parse_result.query = self.query.copy()

        return result

    @with_connection
    def copy(self, other, options=None, ignore=None):
        """
        copy: copy self to other

        @type other: URI
        @param other: the path to copy itself over.

        What will really happen depends on the backend.
        """
        return self.connection.copy(self, other, options, ignore)

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
    def remove(self, options=None):
        """
        remove: shortcut method to remove self.
        if 'self' represents a file, the backends 'removefile' method id used.
        if 'self' represents a directory, it will recursivly removed, if
        the options string contains 'r'. Otherwise, the backends 'removedir'
        method is used.
        """
        if self.connection.isfile(self):
            return self.connection.removefile(self)
        elif self.connection.isdir(self):
            if options and 'r' in options:
                for root, dirs, files in self.connection.walk(
                    self,
                    topdown=False
                    ):
                    for fname in files:
                        self.connection.removefile(root / fname)
                    for dname in dirs:
                        self.connection.removedir(root / dname)
            return self.connection.removedir(self)

    @with_connection
    def open(self, options=None):
        """
        open: return a file like object for self.
        The method can be used with the 'with' statment.
        """
        return self.connection.open(self, options)

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
    def walk(self):
        """
        walk: walk the filesystem (just like os.walk).
        Use like:

        path = URI('/some/dir')
        for root, dirs, files in path.walk():
            do_something()

        root will be an URI object.
        """
        return self.connection.walk(self)

    @with_connection
    def listdir(self, options=None):
        """
        listdir: list contents of directory self.
        if options == 'r', return the content of this
        directory recursivly. The pathpart of 'self' will
        not be returned.
        """
        # TODO-std: shouldn't this return URIs?
        return self.connection.listdir(self, options)

    @property
    @with_connection
    def info(self):
        """
        info: backend info about self (probably not implemented for
              all backends. The result will be backend specific

        @rtype: Bunch
        @return: backend specific information about self.
        """
        return self.connection.info(self)

    @with_connection
    def update(self, recursive=True, clean=False):
        return self.connection.update(self, recursive, clean)

    @with_connection
    def sync(self, other, options=''):
        return self.connection.sync(self, other, options)

    @with_connection
    def log(self, limit=0):
        return self.connection.log(self, limit)

    @with_connection
    def log_by_time(self, start_time=None, stop_time=None):
        return self.connection.log_by_time(self, start_time, stop_time)


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
        with self.open() as inf:
            block = inf.read(4096)
            while block:
                hash_.update(block)
                block = inf.read(4096)

        return hash_.hexdigest()[1:-1]


    @with_connection
    def mtime(self):
        """
        Returns the modification-time in seconds since the epoch,
        as returned by time.time()
        """
        self.connection.mtime(self)


#============================================================================

class FileSystem(object):
    """
    FileSystem is the base class for any file system.

    Some default implementations are provided for some higher functions like
    copy, makedirs, etc.
    """

    scheme = None

    def __init__(
        self,
        hostname=None,
        port=None,
        username=None,
        password=None,
        **extras
        ):
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        self.extras = extras
        self.last_used = time.time()

        self._initialize()

    def close(self):
        pass

    def _path(self, uriobj):
        if isinstance(uriobj, URI):
            return uriobj.path
        else:
            return uriobj


    def copy(self, source, dest, options=None, ignore=None):
        if source.connection is dest.connection:
            return self.internal_copy(source, dest, options, ignore)

        # TODO-std: what about options and ignore, ovewriting files
        # directories and so forth
        # copy over two different FileSystem-types
        assert source.isfile()
        with source.open() as inf:
            content = inf.read()
        with dest.open("w") as outf:
            outf.write(content)



#-- default implementations -------------------------------------------------

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
            source.copy(destination, 'r')
            source.remove('r')


    def walk(self, top, topdown=True):
        names = self.listdir(top)

        dirs, nondirs = [], []
        for name in names:
            if self.isdir(top / name):
                dirs.append(name)
            else:
                nondirs.append(name)

        if topdown:
            yield top, dirs, nondirs
        for name in dirs:
            path = top / name
            for x in self.walk(path, topdown):
                yield x
        if not topdown:
            yield top, dirs, nondirs


    def glob(self, path, pattern):
        # TODO-std: is this working with separators?
        res = []
        for f in path.listdir():
            f = path / f
            if fnmatch.fnmatch(self._path(f), pattern):
                res.append(f)
        return res


#-- overwritable methods ----------------------------------------------------

    def _initialize(self):
        raise NotImplementedError

    def open(self, path, options):
        raise NotImplementedError

    def listdir(self, path, options=None):
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

    def info(self,  path):
        raise NotImplementedError

    def update(self,  path):
        raise NotImplementedError

    def sync(self, source, dest, options):
        raise NotImplementedError

    def log(self, path, limit=0):
        raise NotImplementedError

    def log_by_time(self, path, start_time=None, stop_time=None):
        raise NotImplementedError

    def internal_copy(self, source, dest, options=None, ignore=None):
        raise NotImplementedError

    def mtime(self, path):
        raise NotImplementedError


for entrypoint in pkg_resources.iter_entry_points('abl.vpath.plugins'):
    try:
        plugin_class = entrypoint.load()
    except Exception, exp:
        print "Could not load entrypoint", entrypoint
        traceback.print_exc()
        continue
    CONNECTION_REGISTRY.register(plugin_class.scheme, plugin_class)
