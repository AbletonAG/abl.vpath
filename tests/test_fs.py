#******************************************************************************
# (C) 2013 Ableton AG
#******************************************************************************

from __future__ import with_statement
import datetime
import os
import time
import tempfile
import stat
import sys
from posixpath import join as ujoin
from unittest import TestCase
import logging
import shutil
from common import create_file, os_create_file, load_file, mac_only, windows_only
from abl.vpath.base import *
from abl.vpath.base.fs import CONNECTION_REGISTRY


class CommonFileSystemTest(TestCase):
    def setUp(self):
        self.local_setup()
        self.foo_path = URI(self.baseurl) / 'foo'
        self.existing_dir = ujoin(self.baseurl, 'foo')
        self.existing_file = ujoin(self.baseurl, 'foo', 'foo.txt')
        self.non_existing_file = ujoin(self.baseurl, 'bar.txt')


    def tearDown(self):
        self.local_teardown()


    def file(self):
        if self.writable:
            path = URI(self.baseurl) / 'testfile.txt'
            create_file(path, content='hallo')
            content = load_file(path)

            self.assertEqual(content, 'hallo')
            self.assert_(path.exists())
            self.assert_(path.isfile())
            path.remove()
            self.assert_(not path.exists())

        path = URI(self.existing_file)
        self.assert_(path.exists())
        self.assert_(path.isfile())

        content = load_file(path)
        self.assert_(content)


    def dir(self):
        if self.writable:
            testdir = URI('testdir')
            testdir.makedirs()
            self.assert_(testdir.exists())
            self.assert_(testdir.isdir())
            self.assert_(not testdir.isfile())
            testfile = URI('testdir/somefile')
            create_file(testfile, content='test')
            testdir.remove(recursive=True)
            self.assert_(not testdir.exists())
            self.assert_(not testfile.exists())

        testdir = URI(self.existing_dir)
        self.assert_(testdir.exists())
        self.assert_(testdir.isdir())


    def listdir(self):
        path = URI(self.existing_dir)
        dirs = path.listdir()
        self.assert_('foo.txt' in dirs)


    def walk(self):
        if self.walkable:
            path = URI(self.existing_dir)
            for root, dirs, files in path.walk():
                if path == root:
                    self.assert_('foo.txt' in files)
                    self.assert_('bar' in dirs)


    def relative_walk(self):
        if self.walkable:
            path = URI(self.existing_dir)
            for root, relative, dirs, files in path.relative_walk():
                if path == root:
                    self.assert_('foo.txt' in files)
                    self.assert_('bar' in dirs)
                    self.assertEqual(relative, '')
                if relative == 'bar':
                    self.assert_(not dirs)
                    self.assert_(not files)


    def copy_and_move_file(self):
        if self.writable:
            single_file = URI(self.non_existing_file)
            target_file = URI(self.baseurl) / 'target_file.txt'
            create_file(single_file)

            single_file.copy(target_file)
            self.assert_(target_file.exists())
            self.assert_(target_file.isfile())
            self.assertEqual(load_file(target_file), 'content')

            target_file.remove()
            self.assert_(not target_file.exists())
            single_file.move(target_file)

            self.assert_(not single_file.exists())
            self.assert_(target_file.exists())
            self.assert_(target_file.isfile())

            self.assertEqual(load_file(target_file), 'content')
            target_file.remove()


    def copy_and_move_dir(self):
        if self.writable:
            folder = URI(self.baseurl) / 'folder'
            folder.makedirs()

            self.assert_(folder.isdir())
            afile = folder / 'afile.txt'
            create_file(afile)

            target = URI(self.baseurl) / 'target'
            self.assert_(not target.exists())
            folder.copy(target, recursive=True)
            self.assert_(target.exists())

            target_file = target / 'afile.txt'
            self.assert_(target_file.exists())
            self.assertEqual(load_file(target_file), 'content')

            target.remove(recursive=True)
            self.assert_(not target.exists())
            target.makedirs()
            folder.copy(target, recursive=True)

            newtarget = target / 'folder'
            self.assert_(newtarget.exists())
            self.assert_(newtarget.isdir())

            newtarget_file = newtarget / 'afile.txt'
            self.assert_(newtarget_file.exists())
            self.assert_(newtarget_file.isfile())
            target.remove(recursive=True)

            folder.move(target)
            self.assert_(not folder.exists())
            self.assert_(target.exists())
            self.assert_(target.isdir())
            self.assert_(target_file.exists())
            self.assert_(target_file.isfile())
            target.remove(recursive=True)


    def move_folder_to_subfolder(self):
        """Test moving a directory '/some/path/folder' to '/some/path/target'.
        '/some/path/target' does already exist.  It is expected that after
        the move '/some/path/target/folder' exists.
        """
        folder = self.foo_path / 'folder'
        content = folder / 'content_dir'
        and_more = content / 'and_more'
        and_more.makedirs()

        target = self.foo_path / 'target'
        target.makedirs()

        folder.move(target)

        self.assert_(not folder.exists())
        self.assert_(target.exists())
        self.assert_('folder' in target.listdir())
        self.assert_((target / 'folder').isdir())
        self.assert_((target / 'folder' / 'content_dir').isdir())


    def rename_folder(self):
        """Test moving a directory '/some/path/folder' to '/some/path/target'.
        '/some/path/target' does NOT yet exist.  It is expected that after
        the move '/some/path/target' exists and is actually the former
        '/some/path/folder'.
        """
        folder = self.foo_path / 'folder'
        content = folder / 'content_dir'
        and_more = content / 'and_more'

        and_more.makedirs()

        target = self.foo_path / 'target'
        folder.move(target)

        self.assert_(not folder.exists())
        self.assert_(target.isdir())
        self.assert_('content_dir' in target.listdir())


class TestLocalFileSystem(CommonFileSystemTest):
    def local_setup(self):
        self.writable = True
        self.walkable = True
        thisdir = os.path.split(os.path.abspath(__file__))[0]
        self.tmpdir = tempfile.mkdtemp('.temp', 'test-local-fs', thisdir)
        self.baseurl = 'file://' + self.tmpdir

        foo_dir = os.path.join(self.tmpdir, 'foo')
        bar_dir = os.path.join(foo_dir, 'bar')
        os.makedirs(foo_dir)
        os.makedirs(bar_dir)

        some_file = os.path.join(foo_dir, 'foo.txt')
        os_create_file(some_file)


    def local_teardown(self):
        shutil.rmtree(self.tmpdir)


    def test_file(self):
        super(TestLocalFileSystem, self).file()

    def test_dir(self):
        super(TestLocalFileSystem, self).dir()

    def test_listdir(self):
        super(TestLocalFileSystem, self).listdir()

    def test_walk(self):
        super(TestLocalFileSystem, self).walk()

    def test_relative_walk(self):
        super(TestLocalFileSystem, self).relative_walk()

    def test_copy_and_move_file(self):
        super(TestLocalFileSystem, self).copy_and_move_file()

    def test_copy_and_move_dir(self):
        super(TestLocalFileSystem, self).copy_and_move_dir()

    def test_move_folder_to_subfolder(self):
        super(TestLocalFileSystem, self).move_folder_to_subfolder()

    def test_rename_folder(self):
        super(TestLocalFileSystem, self).rename_folder()


class TestMemoryFileSystem(CommonFileSystemTest):
    def local_setup(self):
        self.writable = True
        self.walkable = True
        CONNECTION_REGISTRY.cleanup(force=True)
        self.baseurl = "memory:///"

        foo_path = URI(self.baseurl) / 'foo'
        bar_path = foo_path / 'bar'
        bar_path.makedirs()

        some_path = foo_path / 'foo.txt'
        create_file(some_path)


    def local_teardown(self):
        pass


    def test_file(self):
        super(TestMemoryFileSystem, self).file()

    def test_dir(self):
        super(TestMemoryFileSystem, self).dir()

    def test_listdir(self):
        super(TestMemoryFileSystem, self).listdir()

    def test_walk(self):
        super(TestMemoryFileSystem, self).walk()

    def test_relative_walk(self):
        super(TestMemoryFileSystem, self).relative_walk()

    def test_copy_and_move_file(self):
        super(TestMemoryFileSystem, self).copy_and_move_file()

    def test_copy_and_move_dir(self):
        super(TestMemoryFileSystem, self).copy_and_move_dir()

    def test_move_folder_to_subfolder(self):
        super(TestMemoryFileSystem, self).move_folder_to_subfolder()

    def test_rename_folder(self):
        super(TestMemoryFileSystem, self).rename_folder()


#-------------------------------------------------------------------------------

class CommonFSCopyTest(TestCase):
    def copystat_exec_to_nonexec(self):
        root = URI(self.baseurl)

        # create a file with execution flag
        xfile = create_file(root / 'xfile.exe')
        xfile.set_exec(stat.S_IXUSR)

        # create a file without exec flag
        ofile = create_file(root / 'otherfile.exe')

        xfile.copystat(ofile)

        self.assert_(ofile.isexec())


    def copystat_nonexec_to_exec(self):
        root = URI(self.baseurl)

        # create a file with execution flag
        xfile = create_file(root / 'xfile.sh')
        xfile.set_exec(stat.S_IXUSR)

        # create a file without exec flag
        ofile = create_file(root / 'otherfile.txt')

        ofile.copystat(xfile)

        self.assert_(not xfile.isexec())


    def copy_recursive(self):
        root = URI(self.baseurl)
        foo_path = root / 'foo'
        foo_path.mkdir()

        bar_path = root / 'bar'

        # create a file with execution flag
        xfile = create_file(foo_path / 'xfile.exe')
        xfile.set_exec(stat.S_IXUSR)

        zfile = create_file(foo_path / 'zfile.exe')
        zfile.set_exec(stat.S_IXUSR)

        # create a file without exec flag
        ofile = create_file(foo_path / 'otherfile.txt')
        nfile = create_file(foo_path / 'nfile.txt')

        foo_path.copy(bar_path, recursive=True)

        self.assert_((bar_path / 'xfile.exe').isexec())
        self.assert_((bar_path / 'zfile.exe').isexec())
        self.assert_(not (bar_path / 'otherfile.txt').isexec())
        self.assert_(not (bar_path / 'nfile.txt').isexec())


    def copy_dir_to_file(self):
        root = URI(self.baseurl)
        bar_path = root / 'foo' / 'bar'
        bar_path.makedirs()
        gaz_path = bar_path / 'gaz.txt'
        create_file(gaz_path, content='foobar')

        moo_path = root / 'moo.txt'
        create_file(moo_path, content='moomoo')

        # can't copy dir on (existing) file
        self.failUnlessRaises(OSError, bar_path.copy,
                              moo_path, recursive=True)


    def copy_empty_dirs_recursive(self):
        root = URI(self.baseurl)
        root.makedirs()

        gaz_path = root / 'gaz'
        gaz_path.makedirs()

        moo_path = root / 'moo'

        gaz_path.copy(moo_path, recursive=True)

        self.assert_((moo_path).isdir())


class TestLocalFSCopy2(CommonFSCopyTest):
    def setUp(self):
        thisdir = os.path.split(os.path.abspath(__file__))[0]
        self.tmpdir = tempfile.mkdtemp('.temp', 'test-local-fs', thisdir)
        self.baseurl = 'file://' + self.tmpdir

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_copystat_exec_to_nonexec(self):
        super(TestLocalFSCopy2, self).copystat_exec_to_nonexec()

    def test_copystat_nonexec_to_exec(self):
        super(TestLocalFSCopy2, self).copystat_nonexec_to_exec()

    def test_copy_recursive(self):
        super(TestLocalFSCopy2, self).copy_recursive()

    def test_copy_empty_dirs_recursive(self):
        super(TestLocalFSCopy2, self).copy_empty_dirs_recursive()


class TestMemoryFSCopy2(CommonFSCopyTest):
    def setUp(self):
        CONNECTION_REGISTRY.cleanup(force=True)
        self.baseurl = "memory:///"

    def tearDown(self):
        pass

    def test_copystat_exec_to_nonexec(self):
        super(TestMemoryFSCopy2, self).copystat_exec_to_nonexec()

    def test_copystat_nonexec_to_exec(self):
        super(TestMemoryFSCopy2, self).copystat_nonexec_to_exec()

    def test_copy_recursive(self):
        super(TestMemoryFSCopy2, self).copy_recursive()

    def test_copy_empty_dirs_recursive(self):
        super(TestMemoryFSCopy2, self).copy_empty_dirs_recursive()


#-------------------------------------------------------------------------------

class CommonFSExecTest(TestCase):
    def exec_flags(self):
        root = URI(self.baseurl)

        # create a file with execution flag
        xfile = create_file(root / 'xfile.exe')

        xfile.set_exec(stat.S_IXUSR)
        self.assert_(xfile.isexec())
        self.assertEqual(xfile.info().mode & stat.S_IXUSR, stat.S_IXUSR)

        # create a file without exec flag
        ofile = create_file(root / 'otherfile.txt')

        self.assertEqual(ofile.info().mode & stat.S_IXUSR, 0)
        self.assert_(not ofile.isexec())


class TestLocalFSExec(CommonFSExecTest):
    def setUp(self):
        thisdir = os.path.split(os.path.abspath(__file__))[0]
        self.tmpdir = tempfile.mkdtemp('.temp', 'test-local-fs', thisdir)
        self.baseurl = 'file://' + self.tmpdir

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_exec_flags(self):
        super(TestLocalFSExec, self).exec_flags()


class TestMemoryFSExec(CommonFSExecTest):
    def setUp(self):
        CONNECTION_REGISTRY.cleanup(force=True)
        self.baseurl = "memory:///"

    def tearDown(self):
        pass

    def test_exec_flags(self):
        super(TestMemoryFSExec, self).exec_flags()


