#******************************************************************************
# (C) 2008-2013 Ableton AG
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


#-------------------------------------------------------------------------------

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
