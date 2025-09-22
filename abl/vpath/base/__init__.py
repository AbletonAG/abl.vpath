"""
``abl.vpath`` provides an extensible abstraction over one or more file
systems.  Paths are represented as URI objects that expose a familiar API
inspired by :mod:`os.path`, while adapters ("connectors") translate each
operation into calls against a concrete backend.

Core concepts
-------------
* :class:`~abl.vpath.base.fs.URI` and
  :class:`~abl.vpath.base.fs.RevisionedUri` wrap filesystem paths and provide
  helpers such as :meth:`exists`, :meth:`open`, and the ``/`` operator for
  joining paths.
* :class:`~abl.vpath.base.fs.FileSystem` defines the contract that backends
  must implement so that URI instances can talk to the underlying storage.
* :class:`~abl.vpath.base.misc.WorkingDirectory` temporarily switches the
  process' working directory while code interacts with a URI.

Usage example::

    from abl.vpath.base import URI, WorkingDirectory

    project_root = URI('file:///tmp/my-project')
    (project_root / 'data').makedirs()
    with (project_root / 'README.txt').open('w') as handle:
        handle.write('hello from vpath\n')

    with WorkingDirectory(project_root):
        print(URI('file://./README.txt').open().read())

Connectors are discovered via the ``abl.vpath.plugins`` entry point group.
This package ships with handlers for:

* ``file`` – local POSIX and Windows file systems (:class:`LocalFileSystem`)
* ``memory`` – an in-memory filesystem useful for tests (:class:`MemoryFileSystem`)
* ``zip`` – transparent access to members inside ZIP archives
  (:class:`ZipFileSystem`)
"""

from .fs import URI, FileSystem, BaseUri, RevisionedFileSystem, RevisionedUri
from .misc import WorkingDirectory
from .exceptions import *

import logging
from abl.util import NullHandler

logging.getLogger("abl.vpath").addHandler(NullHandler())
