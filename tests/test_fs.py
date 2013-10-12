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
from unittest import TestCase
import logging
import shutil
from common import create_file, load_file, mac_only, windows_only
from abl.vpath.base import *
from abl.vpath.base.fs import CONNECTION_REGISTRY


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
        self.thisdir = os.path.split(os.path.abspath(__file__))[0]
        self.tmpdir = tempfile.mkdtemp('.temp', 'test-local-fs', self.thisdir)
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
        self.thisdir = os.path.split(os.path.abspath(__file__))[0]
        self.tmpdir = tempfile.mkdtemp('.temp', 'test-local-fs', self.thisdir)
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


