#******************************************************************************
# (C) 2009 Ableton AG
# author: Stephan Diehl (std)
# email: stephan.diehl@ableton.com
#******************************************************************************
from __future__ import with_statement
import datetime
import os
import time
import tempfile
import stat
import sys
from unittest import TestCase
from abl.vpath.base import *
import logging
import shutil
from common import create_file, load_file, mac_only, windows_only


class TestLocalFSInfo(TestCase):
    def setUp(self):
        self.starttime = datetime.datetime.now()
        p = URI("test.txt")
        with p.open("w") as fs:
            fs.write('test')


    def tearDown(self):
        p = URI("test.txt")
        if p.exists():
            p.remove()


    def test_info_ctime(self):
        p = URI("test.txt")
        self.assert_(p.info().ctime <= datetime.datetime.now())
        self.assertEqual(p.info().ctime, p.info().mtime)


    def test_info_mtime(self):
        p = URI("test.txt")
        now = datetime.datetime.now()
        size = p.info().size
        with p.open('a') as fs:
            fs.write(' again')
        self.assert_(p.info().mtime >= p.info().ctime)
        self.assert_( p.info().size > size)
        # due to now's millisecond resolution, we must ignore milliseconds
        self.assert_(p.info().mtime.timetuple()[:6] >= now.timetuple()[:6])


    def test_locking(self):
        try:
            p = URI("lock.txt")
            content = "I'm something written into a locked file"
            with p.lock() as inf:
                inf.write(content)
            self.assertEqual(p.open().read(), content)
        finally:
            if p.exists():
                p.remove()


    def test_setting_mode(self):
        # setting the permission flags are not supported on windows
        if sys.platform != "win32":
            p = URI("test.txt")
            mode = p.info().mode
            new_mode = mode | stat.S_IXUSR
            p.info(dict(mode=new_mode))
            self.assertEqual(
                p.info().mode,
                new_mode,
                )


class TestLocalFSExec(TestCase):
    def setUp(self):
        self.thisdir = os.path.split(os.path.abspath(__file__))[0]
        self.tmpdir = tempfile.mkdtemp('.temp', 'test-local-fs', self.thisdir)
        self.baseurl = 'file://' + self.tmpdir

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_exec_flags(self):
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


class TestLocalFSCopy(TestCase):
    def setUp(self):
        self.thisdir = os.path.split(os.path.abspath(__file__))[0]
        self.tmpdir = tempfile.mkdtemp('.temp', 'test-local-fs', self.thisdir)
        self.baseurl = 'file://' + self.tmpdir

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


    def test_copystat_exec_to_nonexec(self):
        root = URI(self.baseurl)

        # create a file with execution flag
        xfile = create_file(root / 'xfile.exe')
        xfile.set_exec(stat.S_IXUSR)

        # create a file without exec flag
        ofile = create_file(root / 'otherfile.exe')

        xfile.copystat(ofile)

        self.assert_(ofile.isexec())


    def test_copystat_nonexec_to_exec(self):
        root = URI(self.baseurl)

        # create a file with execution flag
        xfile = create_file(root / 'xfile.sh')
        xfile.set_exec(stat.S_IXUSR)

        # create a file without exec flag
        ofile = create_file(root / 'otherfile.txt')

        ofile.copystat(xfile)

        self.assert_(not xfile.isexec())


    def test_copy_recursive(self):
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


    def test_copy_dir_to_file(self):
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


class TestLocalFSSymlink(TestCase):
    def setUp(self):
        self.thisdir = os.path.split(os.path.abspath(__file__))[0]
        self.tmpdir = tempfile.mkdtemp('.temp', 'test-local-fs', self.thisdir)
        self.baseurl = 'file://' + self.tmpdir


    def tearDown(self):
        shutil.rmtree(self.tmpdir)


    @mac_only
    def test_symlink_dir(self):
        root = URI(self.baseurl)
        bar_path = root / 'foo' / 'bar'
        bar_path.makedirs()

        create_file(bar_path / 'gaz.txt')

        moo_path = root / 'moo'

        self.assert_(not moo_path.exists())
        self.assert_(not moo_path.islink())

        bar_path.symlink(moo_path)

        self.assert_(moo_path.exists())
        self.assert_(moo_path.islink())
        # a symlink to a dir is a dir
        self.assert_(moo_path.isdir())

        link = moo_path.readlink()
        self.assert_(link == bar_path)

        # check that gaz.txt is accessible through the symlink
        self.assert_(moo_path / 'gaz.txt')


    @mac_only
    def test_symlink_file(self):
        root = URI(self.baseurl)
        bar_path = root / 'foo' / 'bar'
        bar_path.makedirs()

        gaz_path = bar_path / 'gaz.txt'
        create_file(gaz_path, content='foobar')

        tee_path = root / 'helloworld'

        self.assert_(not tee_path.exists())
        self.assert_(not tee_path.islink())

        gaz_path.symlink(tee_path)

        self.assert_(tee_path.exists())
        self.assert_(tee_path.islink())
        # a symlink to a file is a file
        self.assert_(tee_path.isfile())

        link = tee_path.readlink()
        self.assert_(link == gaz_path)

        # check that gaz.txt is accessible through the symlink
        self.assert_(load_file(tee_path) == 'foobar')


    @mac_only
    def test_copy_filesymlink_to_file_followlinks(self):
        root = URI(self.baseurl)
        bar_path = root / 'foo' / 'bar'
        bar_path.makedirs()

        gaz_path = bar_path / 'gaz.txt'
        create_file(gaz_path, content='foobar')

        tee_path = root / 'helloworld'
        gaz_path.symlink(tee_path)

        moo_path = root / 'moo.txt'
        create_file(moo_path, content='moomoo')

        tee_path.copy(moo_path, followlinks=True)

        self.assert_(not moo_path.islink())
        self.assert_(load_file(moo_path) == 'foobar')


    @mac_only
    def test_copy_filesymlink_to_file_preservelinks(self):
        root = URI(self.baseurl)
        bar_path = root / 'foo' / 'bar'
        bar_path.makedirs()

        gaz_path = bar_path / 'gaz.txt'
        create_file(gaz_path, content='foobar')

        tee_path = root / 'helloworld'
        gaz_path.symlink(tee_path)

        moo_path = root / 'moo2.txt'
        create_file(moo_path, content='moomoo')

        tee_path.copy(moo_path, followlinks=False)

        self.assert_(moo_path.islink())
        self.assert_(load_file(moo_path) == 'foobar')


    @mac_only
    def test_copy_filesymlink_to_dir_followlinks(self):
        root = URI(self.baseurl)
        bar_path = root / 'foo' / 'bar'
        bar_path.makedirs()

        gaz_path = bar_path / 'gaz.txt'
        create_file(gaz_path, content='foobar')

        tee_path = root / 'helloworld'
        gaz_path.symlink(tee_path)

        moo_path = root / 'moo'
        moo_path.makedirs()

        tee_path.copy(moo_path, followlinks=True)

        helloworld_path = moo_path / 'helloworld'
        self.assert_(not helloworld_path.islink())
        self.assert_(load_file(helloworld_path) == 'foobar')


    @mac_only
    def test_copy_filesymlink_to_dir_preservelinks(self):
        root = URI(self.baseurl)
        bar_path = root / 'foo' / 'bar'
        bar_path.makedirs()

        gaz_path = bar_path / 'gaz.txt'
        create_file(gaz_path, content='foobar')

        tee_path = root / 'helloworld'
        gaz_path.symlink(tee_path)

        moo_path = root / 'moo'
        moo_path.makedirs()

        tee_path.copy(moo_path, followlinks=False)

        helloworld_path = moo_path / 'helloworld'
        self.assert_(helloworld_path.islink())
        self.assert_(load_file(helloworld_path) == 'foobar')


    @mac_only
    def test_copy_filesymlink_to_missingfile_followlinks(self):
        root = URI(self.baseurl)
        bar_path = root / 'foo' / 'bar'
        bar_path.makedirs()

        gaz_path = bar_path / 'gaz.txt'
        create_file(gaz_path, content='foobar')

        tee_path = root / 'helloworld'
        gaz_path.symlink(tee_path)

        moo_path = root / 'moo'
        moo_path.makedirs()

        helloworld_path = moo_path / 'helloworld'
        tee_path.copy(helloworld_path, followlinks=True)

        self.assert_(not helloworld_path.islink())
        self.assert_(load_file(helloworld_path) == 'foobar')


    @mac_only
    def test_copy_filesymlink_to_missingfile_preservelinks(self):
        root = URI(self.baseurl)
        bar_path = root / 'foo' / 'bar'
        bar_path.makedirs()

        gaz_path = bar_path / 'gaz.txt'
        create_file(gaz_path, content='foobar')

        tee_path = root / 'helloworld'
        gaz_path.symlink(tee_path)

        moo_path = root / 'moo'
        moo_path.makedirs()

        helloworld_path = moo_path / 'helloworld'
        tee_path.copy(helloworld_path, followlinks=False)

        self.assert_(helloworld_path.islink())
        self.assert_(load_file(helloworld_path) == 'foobar')


    @mac_only
    def test_copy_filesymlink_to_filesymlink_followlinks(self):
        root = URI(self.baseurl)
        bar_path = root / 'foo' / 'bar'
        bar_path.makedirs()

        gaz_path = bar_path / 'gaz.txt'
        create_file(gaz_path, content='foobar')

        gaz2_path = bar_path / 'gaz2.txt'
        create_file(gaz2_path, content='foobar2')

        tee_path = root / 'helloworld'
        gaz_path.symlink(tee_path)

        tee2_path = root / 'helloworld2'
        gaz2_path.symlink(tee2_path)

        tee_path.copy(tee2_path, followlinks=True)

        # when following links copying to a symlink->file modifies the
        # referenced file!
        self.assert_(tee2_path.islink())
        self.assert_(load_file(tee2_path) == 'foobar')
        self.assert_(load_file(gaz2_path) == 'foobar')


    @mac_only
    def test_copy_filesymlink_to_filesymlink_preservelinks(self):
        root = URI(self.baseurl)
        bar_path = root / 'foo' / 'bar'
        bar_path.makedirs()

        gaz_path = bar_path / 'gaz.txt'
        create_file(gaz_path, content='foobar')

        gaz2_path = bar_path / 'gaz2.txt'
        create_file(gaz2_path, content='foobar2')

        tee_path = root / 'helloworld'
        gaz_path.symlink(tee_path)

        tee2_path = root / 'helloworld2'
        gaz2_path.symlink(tee2_path)

        tee_path.copy(tee2_path, followlinks=False)

        self.assert_(tee2_path.islink())
        self.assert_(load_file(tee2_path) == 'foobar')
        self.assert_(tee2_path.readlink() == gaz_path)
        # when preserving links, we don't touch the original file!
        self.assert_(load_file(gaz2_path) == 'foobar2')


    @mac_only
    def test_copy_filesymlink_to_dirsymlink_followlinks(self):
        root = URI(self.baseurl)
        bar_path = root / 'foo' / 'bar'
        bar_path.makedirs()

        gaz_path = bar_path / 'gaz.txt'
        create_file(gaz_path, content='foobar')

        moo_path = root / 'moo'
        moo_path.makedirs()

        tee_path = root / 'helloworld'
        gaz_path.symlink(tee_path)

        tee2_path = root / 'helloworld2'
        moo_path.symlink(tee2_path)

        tee_path.copy(tee2_path, followlinks=True)

        helloworld_path = tee2_path / 'helloworld'

        self.assert_(tee2_path.islink())  # still a link?
        self.assert_(tee_path.islink())  # still a link?

        self.assert_(not helloworld_path.islink())
        self.assert_(helloworld_path.isfile())
        self.assert_(load_file(helloworld_path) == 'foobar')
        self.assert_((moo_path / 'helloworld').isfile())


    @mac_only
    def test_copy_filesymlink_to_dirsymlink_preservelinks(self):
        root = URI(self.baseurl)
        bar_path = root / 'foo' / 'bar'
        bar_path.makedirs()

        gaz_path = bar_path / 'gaz.txt'
        create_file(gaz_path, content='foobar')

        moo_path = root / 'moo'
        moo_path.makedirs()

        tee_path = root / 'helloworld'
        gaz_path.symlink(tee_path)

        tee2_path = root / 'helloworld2'
        moo_path.symlink(tee2_path)

        tee_path.copy(tee2_path, followlinks=False)

        helloworld_path = tee2_path / 'helloworld'

        self.assert_(tee2_path.islink())  # still a link?
        self.assert_(tee_path.islink())  # still a link?

        self.assert_(helloworld_path.islink())
        self.assert_(helloworld_path.isfile())
        self.assert_(load_file(helloworld_path) == 'foobar')
        self.assert_((moo_path / 'helloworld').islink())
        self.assert_((moo_path / 'helloworld').isfile())
        self.assert_(helloworld_path.readlink() == gaz_path)

