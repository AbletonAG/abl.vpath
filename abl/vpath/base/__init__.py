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
from __future__ import absolute_import
from .fs import URI, FileSystem, BaseUri, RevisionedFileSystem, RevisionedUri
from .misc import WorkingDirectory
from exceptions import *

import logging
from abl.util import NullHandler

logging.getLogger("abl.vpath").addHandler(NullHandler())
