#******************************************************************************
# (C) 2009 Ableton AG
# author: Stephan Diehl (std)
# email: stephan.diehl@ableton.com
#******************************************************************************
from __future__ import with_statement
import os

from abl.vpath.base.misc import TempFileHandle


class TestTempFileHandle:
    def test_handle(self):
        fs = open('testfile', 'w')
        fs.write('hallo')
        fs.close()
        with TempFileHandle('testfile') as fs:
            content = fs.read()
        assert content == 'hallo'
        assert not os.path.exists('testfile')

