#******************************************************************************
# (C) 2009 Ableton AG
# author: Stephan Diehl (std)
# email: stephan.diehl@ableton.com
#******************************************************************************

#============================================================================
# Helper Classes

import os
import traceback

class TempFileHandle(object):
    """
    TempFileHandle
    --------------

    remove the (temp) file after closing the handle.
    This is used in the following situation:
    1. place some content into temp file
    2. read the content once
    """
    def __init__(self, tmpfilename):
        self.tmpfilename = tmpfilename
        self.handle = open(self.tmpfilename)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        self.close()

    def read(self, limit=-1):
        return self.handle.read(limit)

    def close(self):
        retval = self.handle.close()
        os.unlink(self.tmpfilename)
        return retval

