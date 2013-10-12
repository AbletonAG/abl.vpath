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
from abl.vpath.base.exceptions import FileDoesNotExistError


#-------------------------------------------------------------------------------

class CommonLocalFSSymlinkLoopTest(TestCase):
    def selfpointing_symlink(self):
        root = URI(self.baseurl)

        tee_path = root / 'helloworld'
        tee_path.symlink(tee_path)

        self.assert_(tee_path.islink())
        self.assert_(tee_path.readlink() == tee_path)


    def listdir_fails_on_selfpointing_symlink(self):
        root = URI(self.baseurl)
        tee_path = root / 'helloworld'
        tee_path.symlink(tee_path)
        self.failUnlessRaises(OSError, tee_path.listdir)


    def open_fails_on_selfpointing_symlink(self):
        root = URI(self.baseurl)
        tee_path = root / 'helloworld'
        tee_path.symlink(tee_path)
        self.failUnlessRaises(IOError, load_file, tee_path)
        self.failUnlessRaises(IOError, create_file, tee_path)


    def isexec_fails_on_selfpointing_symlink(self):
        root = URI(self.baseurl)
        tee_path = root / 'helloworld'
        tee_path.symlink(tee_path)
        self.failUnlessRaises(OSError, tee_path.isexec)


    def set_exec_fails_on_selfpointing_symlink(self):
        root = URI(self.baseurl)
        tee_path = root / 'helloworld'
        tee_path.symlink(tee_path)
        self.failUnlessRaises(OSError, tee_path.set_exec, stat.S_IXUSR | stat.S_IXGRP)


    def remove_fails_on_selfpointing_symlink(self):
        root = URI(self.baseurl)
        tee_path = root / 'helloworld'
        tee_path.symlink(tee_path)
        self.failUnlessRaises(FileDoesNotExistError, tee_path.remove)


    def copystat_fails_on_selfpointing_symlink(self):
        root = URI(self.baseurl)
        bar_path = root / 'gaz.txt'
        create_file(bar_path)

        tee_path = root / 'helloworld'
        tee_path.symlink(tee_path)

        self.failUnlessRaises(OSError, bar_path.copystat, tee_path)
        self.failUnlessRaises(OSError, tee_path.copystat, bar_path)


    def isdir_doesnt_fail_on_selfpointing_symlink(self):
        root = URI(self.baseurl)
        tee_path = root / 'helloworld'
        tee_path.symlink(tee_path)
        self.assert_(not tee_path.isdir())


    def isfile_doesnt_fail_on_selfpointing_symlink(self):
        root = URI(self.baseurl)
        tee_path = root / 'helloworld'
        tee_path.symlink(tee_path)
        self.assert_(not tee_path.isfile())


    def exists_doesnt_fail_on_selfpointing_symlink(self):
        root = URI(self.baseurl)
        tee_path = root / 'helloworld'
        tee_path.symlink(tee_path)
        self.assert_(not tee_path.exists())


    #------------------------------

    def symlink_loop(self):
        root = URI(self.baseurl)
        foo_path = root / 'foo'
        bar_path = foo_path / 'foo'
        bar_path.makedirs()
        tee_path = bar_path / 'tee'
        foo_path.symlink(tee_path)

        self.assert_(tee_path.islink())
        self.assert_(tee_path.readlink() == foo_path)


    def listdir_doesnt_fail_on_symlink_loop(self):
        root = URI(self.baseurl)
        foo_path = root / 'foo'
        bar_path = foo_path / 'foo' / 'bar'
        bar_path.makedirs()
        tee_path = bar_path / 'tee'
        foo_path.symlink(tee_path)

        moo_path = foo_path / 'moo.txt'
        create_file(moo_path)

        self.assert_('moo.txt' in tee_path.listdir())


    def open_fails_on_symlink_loop(self):
        root = URI(self.baseurl)
        tee_path = root / 'helloworld'
        tee_path.symlink(tee_path)
        self.failUnlessRaises(IOError, load_file, tee_path)
        self.failUnlessRaises(IOError, create_file, tee_path)


    def isexec_fails_on_symlink_loop(self):
        root = URI(self.baseurl)
        tee_path = root / 'helloworld'
        tee_path.symlink(tee_path)
        self.failUnlessRaises(OSError, tee_path.isexec)


    def set_exec_fails_on_symlink_loop(self):
        root = URI(self.baseurl)
        tee_path = root / 'helloworld'
        tee_path.symlink(tee_path)
        self.failUnlessRaises(OSError, tee_path.set_exec, stat.S_IXUSR | stat.S_IXGRP)


    def remove_fails_on_symlink_loop(self):
        root = URI(self.baseurl)
        tee_path = root / 'helloworld'
        tee_path.symlink(tee_path)
        self.failUnlessRaises(FileDoesNotExistError, tee_path.remove)


    def copystat_fails_on_symlink_loop(self):
        root = URI(self.baseurl)
        bar_path = root / 'gaz.txt'
        create_file(bar_path)

        tee_path = root / 'helloworld'
        tee_path.symlink(tee_path)

        self.failUnlessRaises(OSError, bar_path.copystat, tee_path)
        self.failUnlessRaises(OSError, tee_path.copystat, bar_path)


    def isdir_doesnt_fail_on_symlink_loop(self):
        root = URI(self.baseurl)
        tee_path = root / 'helloworld'
        tee_path.symlink(tee_path)
        self.assert_(not tee_path.isdir())


    def isfile_doesnt_fail_on_symlink_loop(self):
        root = URI(self.baseurl)
        tee_path = root / 'helloworld'
        tee_path.symlink(tee_path)
        self.assert_(not tee_path.isfile())


    def exists_doesnt_fail_on_symlink_loop(self):
        root = URI(self.baseurl)
        tee_path = root / 'helloworld'
        tee_path.symlink(tee_path)
        self.assert_(not tee_path.exists())



class TestLocalFSSymlinkLoop(CommonLocalFSSymlinkLoopTest):
    def setUp(self):
        self.thisdir = os.path.split(os.path.abspath(__file__))[0]
        self.tmpdir = tempfile.mkdtemp('.temp', 'test-local-fs', self.thisdir)
        self.baseurl = 'file://' + self.tmpdir


    def tearDown(self):
        shutil.rmtree(self.tmpdir)


    @mac_only
    def test_selfpointing_symlink(self):
        super(TestLocalFSSymlinkLoop, self).selfpointing_symlink()

    @mac_only
    def test_listdir_fails_on_selfpointing_symlink(self):
        super(TestLocalFSSymlinkLoop, self).listdir_fails_on_selfpointing_symlink()

    @mac_only
    def test_open_fails_on_selfpointing_symlink(self):
        super(TestLocalFSSymlinkLoop, self).open_fails_on_selfpointing_symlink()

    @mac_only
    def test_isexec_fails_on_selfpointing_symlink(self):
        super(TestLocalFSSymlinkLoop, self).isexec_fails_on_selfpointing_symlink()

    @mac_only
    def test_set_exec_fails_on_selfpointing_symlink(self):
        super(TestLocalFSSymlinkLoop, self).set_exec_fails_on_selfpointing_symlink()

    @mac_only
    def test_remove_fails_on_selfpointing_symlink(self):
        super(TestLocalFSSymlinkLoop, self).remove_fails_on_selfpointing_symlink()

    @mac_only
    def test_copystat_fails_on_selfpointing_symlink(self):
        super(TestLocalFSSymlinkLoop, self).copystat_fails_on_selfpointing_symlink()

    @mac_only
    def test_isdir_doesnt_fail_on_selfpointing_symlink(self):
        super(TestLocalFSSymlinkLoop, self).isdir_doesnt_fail_on_selfpointing_symlink()

    @mac_only
    def test_isfile_doesnt_fail_on_selfpointing_symlink(self):
        super(TestLocalFSSymlinkLoop, self).isfile_doesnt_fail_on_selfpointing_symlink()

    @mac_only
    def test_exists_doesnt_fail_on_selfpointing_symlink(self):
        super(TestLocalFSSymlinkLoop, self).exists_doesnt_fail_on_selfpointing_symlink()


    @mac_only
    def test_symlink_loop(self):
        super(TestLocalFSSymlinkLoop, self).symlink_loop()

    @mac_only
    def test_listdir_doesnt_fail_on_symlink_loop(self):
        super(TestLocalFSSymlinkLoop, self).listdir_doesnt_fail_on_symlink_loop()

    @mac_only
    def test_open_fails_on_symlink_loop(self):
        super(TestLocalFSSymlinkLoop, self).open_fails_on_symlink_loop()

    @mac_only
    def test_isexec_fails_on_symlink_loop(self):
        super(TestLocalFSSymlinkLoop, self).isexec_fails_on_symlink_loop()

    @mac_only
    def test_set_exec_fails_on_symlink_loop(self):
        super(TestLocalFSSymlinkLoop, self).set_exec_fails_on_symlink_loop()

    @mac_only
    def test_remove_fails_on_symlink_loop(self):
        super(TestLocalFSSymlinkLoop, self).remove_fails_on_symlink_loop()

    @mac_only
    def test_copystat_fails_on_symlink_loop(self):
        super(TestLocalFSSymlinkLoop, self).copystat_fails_on_symlink_loop()

    @mac_only
    def test_isdir_doesnt_fail_on_symlink_loop(self):
        super(TestLocalFSSymlinkLoop, self).isdir_doesnt_fail_on_symlink_loop()

    @mac_only
    def test_isfile_doesnt_fail_on_symlink_loop(self):
        super(TestLocalFSSymlinkLoop, self).isfile_doesnt_fail_on_symlink_loop()

    @mac_only
    def test_exists_doesnt_fail_on_symlink_loop(self):
        super(TestLocalFSSymlinkLoop, self).exists_doesnt_fail_on_symlink_loop()


class TestMemoryFSSymlinkLoop(CommonLocalFSSymlinkLoopTest):
    def setUp(self):
        CONNECTION_REGISTRY.cleanup(force=True)
        self.baseurl = "memory:///"

    def tearDown(self):
        pass

    def test_selfpointing_symlink(self):
        super(TestMemoryFSSymlinkLoop, self).selfpointing_symlink()

    def test_listdir_fails_on_selfpointing_symlink(self):
        super(TestMemoryFSSymlinkLoop, self).listdir_fails_on_selfpointing_symlink()

    def test_open_fails_on_selfpointing_symlink(self):
        super(TestMemoryFSSymlinkLoop, self).open_fails_on_selfpointing_symlink()

    def test_isexec_fails_on_selfpointing_symlink(self):
        super(TestMemoryFSSymlinkLoop, self).isexec_fails_on_selfpointing_symlink()

    def test_set_exec_fails_on_selfpointing_symlink(self):
        super(TestMemoryFSSymlinkLoop, self).set_exec_fails_on_selfpointing_symlink()

    def test_remove_fails_on_selfpointing_symlink(self):
        super(TestMemoryFSSymlinkLoop, self).remove_fails_on_selfpointing_symlink()

    def test_copystat_fails_on_selfpointing_symlink(self):
        super(TestMemoryFSSymlinkLoop, self).copystat_fails_on_selfpointing_symlink()

    def test_isdir_doesnt_fail_on_selfpointing_symlink(self):
        super(TestMemoryFSSymlinkLoop, self).isdir_doesnt_fail_on_selfpointing_symlink()

    def test_isfile_doesnt_fail_on_selfpointing_symlink(self):
        super(TestMemoryFSSymlinkLoop, self).isfile_doesnt_fail_on_selfpointing_symlink()

    def test_exists_doesnt_fail_on_selfpointing_symlink(self):
        super(TestMemoryFSSymlinkLoop, self).exists_doesnt_fail_on_selfpointing_symlink()


    def test_symlink_loop(self):
        super(TestMemoryFSSymlinkLoop, self).symlink_loop()

    def test_listdir_doesnt_fail_on_symlink_loop(self):
        super(TestMemoryFSSymlinkLoop, self).listdir_doesnt_fail_on_symlink_loop()

    def test_open_fails_on_symlink_loop(self):
        super(TestMemoryFSSymlinkLoop, self).open_fails_on_symlink_loop()

    def test_isexec_fails_on_symlink_loop(self):
        super(TestMemoryFSSymlinkLoop, self).isexec_fails_on_symlink_loop()

    def test_set_exec_fails_on_symlink_loop(self):
        super(TestMemoryFSSymlinkLoop, self).set_exec_fails_on_symlink_loop()

    def test_remove_fails_on_symlink_loop(self):
        super(TestMemoryFSSymlinkLoop, self).remove_fails_on_symlink_loop()

    def test_copystat_fails_on_symlink_loop(self):
        super(TestMemoryFSSymlinkLoop, self).copystat_fails_on_symlink_loop()

    def test_isdir_doesnt_fail_on_symlink_loop(self):
        super(TestMemoryFSSymlinkLoop, self).isdir_doesnt_fail_on_symlink_loop()

    def test_isfile_doesnt_fail_on_symlink_loop(self):
        super(TestMemoryFSSymlinkLoop, self).isfile_doesnt_fail_on_symlink_loop()

    def test_exists_doesnt_fail_on_symlink_loop(self):
        super(TestMemoryFSSymlinkLoop, self).exists_doesnt_fail_on_symlink_loop()


