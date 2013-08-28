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


def create_file(inpath, name):
    f = inpath / name
    with f.open('w') as fs:
        fs.write('content')
    return f


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
        xfile = create_file(root, 'xfile.exe')

        xfile.set_exec(stat.S_IXUSR)
        self.assert_(xfile.isexec())
        self.assertEqual(xfile.info().mode & stat.S_IXUSR, stat.S_IXUSR)

        # create a file without exec flag
        ofile = create_file(root, 'otherfile.txt')

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
        xfile = create_file(root, 'xfile.exe')
        xfile.set_exec(stat.S_IXUSR)

        # create a file without exec flag
        ofile = create_file(root, 'otherfile.exe')

        xfile.copystat(ofile)

        self.assert_(ofile.isexec())


    def test_copystat_nonexec_to_exec(self):
        root = URI(self.baseurl)

        # create a file with execution flag
        xfile = create_file(root, 'xfile.sh')
        xfile.set_exec(stat.S_IXUSR)

        # create a file without exec flag
        ofile = create_file(root, 'otherfile.txt')

        ofile.copystat(xfile)

        self.assert_(not xfile.isexec())


    def test_copy_recursive(self):
        root = URI(self.baseurl)
        foo_path = root / 'foo'
        foo_path.mkdir()

        bar_path = root / 'bar'

        # create a file with execution flag
        xfile = create_file(foo_path, 'xfile.exe')
        xfile.set_exec(stat.S_IXUSR)

        # create a file without exec flag
        ofile = create_file(foo_path, 'otherfile.txt')

        foo_path.copy(bar_path, recursive=True)

        self.assert_((bar_path / 'xfile.exe').isexec())
        self.assert_(not (bar_path / 'otherfile.txt').isexec())
