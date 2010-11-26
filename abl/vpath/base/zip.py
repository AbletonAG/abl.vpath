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
    def __init__(self, path_string, zip_handle):
        self.path_string = path_string
        self.zip_handle = zip_handle
        self.byte_buffer = StringIO()

    def __enter__(self):
        return self

    def __exit__(self, etype, evalue, etraceback):
        self.zip_handle.writestr(self.path_string, self.byte_buffer.getvalue())
        self.byte_buffer.close()

    def __getattr__(self, attr):
        return getattr(self.byte_buffer, attr)

ISDIR = 1
ISFILE = 2

def compare_path_strings(path1, path2, path_sep='/'):
    return compare_parts(path1.split(path_sep), path2.split(path_sep))

def compare_parts(list1, list2):
    if len(list2) < len(list1):
        return 0
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

    def _initialize(self):
        self.real_zip_file_path = URI(self.vpath_connector)
        self._mode = None
        self._ziphandle = None

    def _open_zip(self, options=None):
        if options is None:
            options = 'r'
        if self._mode is not None and options != self._mode:
            self._ziphandle.close()
        if 'w' in options:
            zip_options = 'a'
        else:
            zip_options = options
        self._ziphandle = zipfile.ZipFile(
            self.real_zip_file_path.open(options),
            zip_options
            )
        self._mode = options

    def open(self, unc, options=None):
        self._open_zip(options)
        if options is None:
            options = 'r'
        path_string = self._path(unc)
        if 'r' in self._mode:
            return self._open_for_reading(unc, options)
        elif 'w' in self._mode:
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
        return WriteStatement(path_string, self._ziphandle)

    def exists(self, unc):
        return self._ispart(unc, (ISDIR, ISFILE))

    def isdir(self, unc):
        return self._ispart(unc, (ISDIR,))

    def isfile(self, unc):
        return self._ispart(unc, (ISFILE,))

    def _ispart(self, unc, expected):
        path_string = self._path(unc)
        for item in self._ziphandle.namelist():
            result = compare_path_strings(path_string, item)
            if result in expected:
                return True
        return False

