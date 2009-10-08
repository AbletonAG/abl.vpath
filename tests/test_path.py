#******************************************************************************
# (C) 2008 Ableton AG
#******************************************************************************
from __future__ import with_statement
import datetime
import os
from posixpath import join as ujoin
import shutil
import tempfile

from nose import with_setup
from abl.vpath.base import *

class KeepCurrentDir:

    def __init__(self, directory):
        self._directory = directory
        self._currentdir = os.getcwd()

    def __enter__(self):
        os.chdir(self._directory)
        return self

    def __exit__(self, *exc_args):
        os.chdir(self._currentdir)


class TestHttpUri(object):
    def test_query(self):
        p = URI('http://storm/this')
        p.query['a'] = 'b'
        assert URI(str(p)) == URI('http://storm/this?a=b')

    def test_query_after_join(self):
        p = URI('http://storm/this')
        p /= 'other'
        assert URI(str(p)) == URI('http://storm/this/other')
        p.query['a'] = 'b'
        assert URI(str(p)) == URI('http://storm/this/other?a=b')


class TestURI(object):

    def test_creation(self):
        local_path = URI('/tmp/this')
        assert local_path.path.split(os.sep) == ['', 'tmp', 'this']
        assert local_path.scheme == 'file'

        path = URI('localpath')
        assert path.path == 'localpath'

        path = URI('trailing/slash/')
        assert path.path == 'trailing/slash/'

    def test_split(self):
        local_path = URI('/some/long/dir/structure')
        pth, tail = local_path.split()
        assert pth == URI('/some/long/dir')
        assert tail == 'structure'

        local_path = URI('somedir')
        pth, tail = local_path.split()
        assert pth == URI('.')
        assert tail == 'somedir'

    def test_windows_repr(self):
        path = URI(r'C:\some\path\on\windows', sep='\\')
        assert path.path == r'C:\some\path\on\windows'
        assert path.uri == '/C/some/path/on/windows'

    def test_split_windows(self):
        path = URI(r'C:\some\path\on\windows', sep='\\')
        pth, tail = path.split()
        assert pth.uri == '/C/some/path/on'
        assert pth.path == r'C:\some\path\on'
        assert pth == URI(r'C:\some\path\on', sep='\\')
        assert tail == 'windows'

    def test_join(self):
        long_path = URI('this/is/a/long/path')
        assert long_path == URI('this') / 'is' / 'a' / 'long' / 'path'

    def test_augmented_join(self):
        testpath = URI('/a')
        testpath /= 'path'
        assert URI('/a/path') == testpath

    def test_adding_suffix(self):
        testpath = URI("/a")
        other = testpath + ".foo"
        assert URI("/a.foo") == other
        testpath += ".bar"
        assert URI("/a.bar") == testpath


class TestFileSystem(object):
    def __init__(self):
        self.local_setup()
        self.existing_dir = ujoin(self.baseurl,'foo')
        self.existing_file = ujoin(self.baseurl, 'foo','foo.txt')
        self.non_existing_file = ujoin(self.baseurl, 'bar.txt')

    def local_setup(self):
        self.writable = True
        self.walkable = True
        thisdir = os.path.split(os.path.abspath(__file__))[0]
        self.baseurl = 'file://' + thisdir
        self.extras = {}

    @classmethod
    def setup(cls):
        thisdir = os.path.split(os.path.abspath(__file__))[0]
        foo_dir = os.path.join(thisdir, 'foo')
        bar_dir = os.path.join(foo_dir, 'bar')
        os.mkdir(foo_dir)
        os.mkdir(bar_dir)
        some_file = os.path.join(foo_dir, 'foo.txt')
        with open(some_file, 'w') as fd:
            fd.write('content')

    @classmethod
    def teardown(cls):
        thisdir = os.path.split(os.path.abspath(__file__))[0]
        foo_dir = os.path.join(thisdir, 'foo')
        shutil.rmtree(foo_dir)

    def test_file(self):
        if self.writable:
            path = URI(self.baseurl, **self.extras) / 'testfile.txt'
            with path.open('w') as fd:
                fd.write('hallo')
            with path.open() as fd:
                content = fd.read()
            assert content == 'hallo'
            assert path.exists()
            assert path.isfile()
            path.remove()
            assert not path.exists()
        path = URI(self.existing_file, **self.extras)
        assert path.exists()
        assert path.isfile()
        with path.open() as fd:
            content = fd.read()
        assert content

    def test_dir(self):
        if self.writable:
            testdir = URI('testdir', **self.extras)
            testdir.makedirs()
            assert testdir.exists()
            assert testdir.isdir()
            assert not testdir.isfile()
            testfile = URI('testdir/somefile', **self.extras)
            with testfile.open('w') as fd:
                fd.write('test')
            testdir.remove('r')
            assert not testdir.exists()
            assert not testfile.exists()
        testdir = URI(self.existing_dir, **self.extras)
        assert testdir.exists()
        assert testdir.isdir()

    def test_listdir(self):
        path = URI(self.existing_dir, **self.extras)
        dirs = path.listdir()
        assert 'foo.txt' in dirs

    def test_walk(self):
        if not self.walkable:
            return
        path = URI(self.existing_dir, **self.extras)
        for root, dirs, files in path.walk():
            if path == root:
                assert 'foo.txt' in files
                assert 'bar' in dirs

    def test_copy_and_move_file(self):
        if not self.writable:
            return
        single_file = URI(self.non_existing_file, **self.extras)
        target_file = URI(self.baseurl, **self.extras) / 'target_file.txt'
        with single_file.open('w') as fs:
            fs.write('content')
        single_file.copy(target_file)
        assert target_file.exists()
        assert target_file.isfile()
        with target_file.open() as fs:
            assert fs.read() == 'content'
        target_file.remove()
        assert not target_file.exists()
        single_file.move(target_file)
        assert not single_file.exists()
        assert target_file.exists()
        assert target_file.isfile()
        with target_file.open() as fs:
            assert fs.read() == 'content'
        target_file.remove()
        single_file.remove()

    def test_copy_and_move_dir(self):
        if not self.writable:
            return
        folder = URI(self.baseurl, **self.extras) / 'folder'
        folder.makedirs()
        assert folder.isdir()
        afile = folder / 'afile.txt'
        with afile.open('w') as fs:
            fs.write('content')
        target = URI(self.baseurl, **self.extras) / 'target'
        assert not target.exists()
        folder.copy(target, 'r')
        assert target.exists()
        target_file = target / 'afile.txt'
        assert target_file.exists()
        with target_file.open() as fs:
            content = fs.read()
            assert content == 'content'
        target.remove('r')
        assert not target.exists()
        target.makedirs()
        folder.copy(target, 'r')
        newtarget = target / 'folder'
        assert newtarget.exists()
        assert newtarget.isdir()
        newtarget_file = newtarget / 'afile.txt'
        assert newtarget_file.exists()
        assert newtarget_file.isfile()
        target.remove('r')

        folder.move(target)
        assert not folder.exists()
        assert target.exists()
        assert target.isdir()
        assert target_file.exists()
        assert target_file.isfile()
        target.remove('r')

