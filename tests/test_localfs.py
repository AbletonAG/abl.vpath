#******************************************************************************
# (C) 2009 Ableton AG
# author: Stephan Diehl (std)
# email: stephan.diehl@ableton.com
#******************************************************************************
from __future__ import with_statement
import datetime
import os
import time
from abl.vpath.base import *

class TestLocalFSInfo:

    def setup_method(self, method):
        self.starttime = datetime.datetime.now()
        p = URI("test.txt")
        with p.open("w") as fs:
            fs.write('test')

    def teardown_method(self, method):
        p = URI("test.txt")
        if p.exists():
            p.remove()

    def test_info_ctime(self):
        p = URI("test.txt")
        assert p.info().ctime <= datetime.datetime.now()
        assert p.info().ctime == p.info().mtime

    def test_info_mtime(self):
        p = URI("test.txt")
        now = datetime.datetime.now()
        size = p.info().size
        with p.open('a') as fs:
            fs.write(' again')
        assert p.info().mtime >= p.info().ctime, (p.info().mtime, p.info().ctime)
        assert p.info().size > size
        # due to now's millisecond resolution, we must ignore milliseconds
        assert p.info().mtime.timetuple()[:6] >= now.timetuple()[:6], (p.info().mtime, now)

