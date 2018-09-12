#******************************************************************************
# (C) 2013 Ableton AG
#******************************************************************************


import os
import tempfile
import stat
from unittest import TestCase
import shutil

from abl.vpath.base import URI

from .common import (
    create_file,
    load_file,
    is_on_mac,
    CleanupMemoryBeforeTestMixin,
)


#-------------------------------------------------------------------------------

class CommonLocalFSSymlinkLoopTest(TestCase):
    __test__ = False

    def test_selfpointing_symlink(self):
        root = URI(self.baseurl)

        tee_path = root / 'helloworld'
        tee_path.symlink(tee_path)

        self.assertTrue(tee_path.islink())
        self.assertEqual(tee_path.readlink(), tee_path)


    def test_listdir_fails_on_selfpointing_symlink(self):
        root = URI(self.baseurl)
        tee_path = root / 'helloworld'
        tee_path.symlink(tee_path)
        self.assertRaises(OSError, tee_path.listdir)


    def test_open_fails_on_selfpointing_symlink(self):
        root = URI(self.baseurl)
        tee_path = root / 'helloworld'
        tee_path.symlink(tee_path)
        self.assertRaises(IOError, load_file, tee_path)
        self.assertRaises(IOError, create_file, tee_path)


    def test_isexec_fails_on_selfpointing_symlink(self):
        root = URI(self.baseurl)
        tee_path = root / 'helloworld'
        tee_path.symlink(tee_path)
        self.assertRaises(OSError, tee_path.isexec)


    def test_set_exec_fails_on_selfpointing_symlink(self):
        root = URI(self.baseurl)
        tee_path = root / 'helloworld'
        tee_path.symlink(tee_path)
        self.assertRaises(OSError, tee_path.set_exec, stat.S_IXUSR | stat.S_IXGRP)


    def test_remove_fails_on_selfpointing_symlink(self):
        root = URI(self.baseurl)
        tee_path = root / 'helloworld'
        tee_path.symlink(tee_path)
        self.assertTrue(tee_path.islink())

        tee_path.remove()

        self.assertTrue(not tee_path.islink())
        self.assertTrue(not tee_path.exists())


    def test_copystat_fails_on_selfpointing_symlink(self):
        root = URI(self.baseurl)
        bar_path = root / 'gaz.txt'
        create_file(bar_path)

        tee_path = root / 'helloworld'
        tee_path.symlink(tee_path)

        self.assertRaises(OSError, bar_path.copystat, tee_path)
        self.assertRaises(OSError, tee_path.copystat, bar_path)


    def test_isdir_doesnt_fail_on_selfpointing_symlink(self):
        root = URI(self.baseurl)
        tee_path = root / 'helloworld'
        tee_path.symlink(tee_path)
        self.assertTrue(not tee_path.isdir())


    def test_isfile_doesnt_fail_on_selfpointing_symlink(self):
        root = URI(self.baseurl)
        tee_path = root / 'helloworld'
        tee_path.symlink(tee_path)
        self.assertTrue(not tee_path.isfile())


    def test_exists_doesnt_fail_on_selfpointing_symlink(self):
        root = URI(self.baseurl)
        tee_path = root / 'helloworld'
        tee_path.symlink(tee_path)
        self.assertTrue(not tee_path.exists())


    #------------------------------

    def test_symlink_loop(self):
        root = URI(self.baseurl)
        foo_path = root / 'foo'
        bar_path = foo_path / 'foo'
        bar_path.makedirs()
        tee_path = bar_path / 'tee'
        foo_path.symlink(tee_path)

        self.assertTrue(tee_path.islink())
        self.assertEqual(tee_path.readlink(), foo_path)


    def test_listdir_doesnt_fail_on_symlink_loop(self):
        root = URI(self.baseurl)
        foo_path = root / 'foo'
        bar_path = foo_path / 'foo' / 'bar'
        bar_path.makedirs()
        tee_path = bar_path / 'tee'
        foo_path.symlink(tee_path)

        moo_path = foo_path / 'moo.txt'
        create_file(moo_path)

        self.assertTrue('moo.txt' in tee_path.listdir())


    def test_open_fails_on_symlink_loop(self):
        root = URI(self.baseurl)
        tee_path = root / 'helloworld'
        tee_path.symlink(tee_path)
        self.assertRaises(IOError, load_file, tee_path)
        self.assertRaises(IOError, create_file, tee_path)


    def test_isexec_fails_on_symlink_loop(self):
        root = URI(self.baseurl)
        tee_path = root / 'helloworld'
        tee_path.symlink(tee_path)
        self.assertRaises(OSError, tee_path.isexec)


    def test_set_exec_fails_on_symlink_loop(self):
        root = URI(self.baseurl)
        tee_path = root / 'helloworld'
        tee_path.symlink(tee_path)
        self.assertRaises(OSError, tee_path.set_exec, stat.S_IXUSR | stat.S_IXGRP)


    def test_remove_doesnt_fail_on_symlink_loop(self):
        root = URI(self.baseurl)
        tee_path = root / 'helloworld'
        tee_path.makedirs()
        foo_path = tee_path / 'foo'
        tee_path.symlink(foo_path)

        tee_path.remove(recursive=True)

        self.assertTrue(not tee_path.exists())


    def test_copystat_fails_on_symlink_loop(self):
        root = URI(self.baseurl)
        bar_path = root / 'gaz.txt'
        create_file(bar_path)

        tee_path = root / 'helloworld'
        tee_path.symlink(tee_path)

        self.assertRaises(OSError, bar_path.copystat, tee_path)
        self.assertRaises(OSError, tee_path.copystat, bar_path)





    def test_filechecks_dont_fail_on_mutual_symlinks(self):
        root = URI(self.baseurl)
        tee_path = root / 'helloworld'
        foo_path = root / 'foo'
        tee_path.symlink(foo_path)
        foo_path.symlink(tee_path)

        self.assertTrue(not foo_path.isdir())
        self.assertTrue(not foo_path.isfile())
        self.assertTrue(not foo_path.exists())
        self.assertTrue(foo_path.islink())


    def test_remove_doesnt_fail_on_mutual_symlinks(self):
        root = URI(self.baseurl)
        tee_path = root / 'helloworld'
        foo_path = root / 'foo'

        foo_path.symlink(tee_path)
        tee_path.symlink(foo_path)

        tee_path.remove(recursive=True)

        self.assertTrue(not tee_path.exists())
        self.assertTrue(foo_path.islink())



class TestLocalFSSymlinkLoop(CommonLocalFSSymlinkLoopTest):
    __test__ = is_on_mac()

    def setUp(self):
        self.thisdir = os.path.split(os.path.abspath(__file__))[0]
        self.tmpdir = tempfile.mkdtemp('.temp', 'test-local-fs', self.thisdir)
        self.baseurl = 'file://' + self.tmpdir


    def tearDown(self):
        shutil.rmtree(self.tmpdir)


class TestMemoryFSSymlinkLoop(CleanupMemoryBeforeTestMixin, CommonLocalFSSymlinkLoopTest):
    __test__ = True

    def setUp(self):
        super(TestMemoryFSSymlinkLoop, self).setUp()
        self.baseurl = "memory:///"

    def tearDown(self):
        pass
