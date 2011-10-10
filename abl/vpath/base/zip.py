#******************************************************************************
# (C) 2010 Ableton AG
# Author: Stephan Diehl <stephan.diehl@ableton.com>
#******************************************************************************
from __future__ import with_statement, absolute_import

from StringIO import StringIO

from .fs import FileSystem, BaseUri, denormalize_path, URI
from .exceptions import FileDoesNotExistError
from . import zipfile26 as zipfile

from abl.util import Bunch

class WriteStatement(object):
    def __init__(self, path_string, zip_backend):
        self.path_string = path_string
        self.zip_backend = zip_backend
        self.byte_buffer = StringIO()

    def __enter__(self):
        return self

    def __exit__(self, etype, evalue, etraceback):
        self.zip_backend._ziphandle.writestr(self.path_string, self.byte_buffer.getvalue())
        self.byte_buffer.close()
        self.zip_backend.close_zip()
        self.zip_backend.open_zip()

    def __getattr__(self, attr):
        return getattr(self.byte_buffer, attr)

ISDIR = 1
ISFILE = 2

def content_item(path1, path2, path_sep='/'):
    """
    if path1 is subpart of path2, get the next path item.
    example:
    path1 = '/foo'
    path2 = '/foo/bar/foo'
    -> 'bar'

    """
    p1_parts = path1.split(path_sep)
    p2_parts = path2.split(path_sep)
    # special case when path1 is root
    if path1 == path_sep and len(p2_parts) >= 2:
        return p2_parts[1]
    if len(p2_parts) <= len(p1_parts):
        return ''
    for i, item in enumerate(p1_parts):
        if item != p2_parts[i]:
            return ''
    return p2_parts[i+1]

def compare_path_strings(path1, path2, path_sep='/'):
    """
    find out, if path1 is a file, or a directory (or unknown).
    """
    if len(path2) < len(path1):
        return 0
    if path1 == path2:
        return ISFILE
    else:
        p1_parts = path1.split(path_sep)
        p2_parts = path2.split(path_sep)
        if len(p2_parts) < len(p1_parts):
            return 0
        else:
            return compare_parts(p1_parts, p2_parts)

def compare_parts(list1, list2):
    """
    if list2 does not start with list1, we can't really check and return 0
    """

    for i, item in enumerate(list1):
        if item != list2[i]:
            return 0
    if len(list2) > len(list1):
        return ISDIR
    else:
        return ISFILE

class ZipFileSystemUri(BaseUri):pass

class ZipFileSystem(FileSystem):
    scheme = 'zip'
    uri = ZipFileSystemUri

    def _zip_file_path(self):
        return URI(self.vpath_connector)

    def _initialize(self):
        self._file_handle = None
        self._ziphandle = None

    def close_zip(self):
        if self._ziphandle is not None:
            self._ziphandle.close()
        if self._file_handle is not None:
            self._file_handle.close()

    def open_zip(self, options=None):
        self.close_zip()
        if options is None or 'r' in options:
            zip_options = 'r'
            options = 'rb'
        if 'w' in options:
            if self._zip_file_path().isfile():
                zip_options = 'a'
                options = 'r+b'
            else:
                zip_options = 'w'
                options = 'wb'

        self._file_handle = self._zip_file_path().open(options)
        self._ziphandle = zipfile.ZipFile(self._file_handle, zip_options)

    def open(self, unc, options=None, mimetype='application/octet-stream'):
        self.open_zip(options)
        if options is None:
            options = 'r'
        path_string = self._path(unc)
        if 'r' in options:
            return self._open_for_reading(unc, options)
        elif 'w' in options:
            return self._open_for_writing(unc, options)

    def _open_for_reading(self, unc, options):
        path_string = self._path(unc)
        try:
            self._ziphandle.getinfo(path_string)
            return self._ziphandle.open(path_string)
        except KeyError:
            raise FileDoesNotExistError()

    def _open_for_writing(self, unc, options):
        path_string = self._path(unc)
        return WriteStatement(path_string, self)

    def exists(self, unc):
        return self._ispart(unc, (ISDIR, ISFILE))

    def isdir(self, unc):
        return self._ispart(unc, (ISDIR,))

    def isfile(self, unc):
        return self._ispart(unc, (ISFILE,))

    def listdir(self, unc, recursive=False):
        if not self._zip_file_path().exists():
            return []
        if self._ziphandle is None:
            self.open_zip()
        path_string = self._path(unc)
        if path_string == '/' and self._ziphandle is None:
            return []
        if not self.isdir(unc):
            raise FileDoesNotExistError()
        content_set = set()
        for item in self._ziphandle.namelist():
            citem = content_item(path_string, item)
            if citem:
                content_set.add(citem)
            
        return list(sorted(content_set))

    def _ispart(self, unc, expected):
        path_string = self._path(unc)
        if path_string == '/':
            return True
        for item in self._ziphandle.namelist():
            result = compare_path_strings(path_string, item)
            if result in expected:
                return True
        return False

