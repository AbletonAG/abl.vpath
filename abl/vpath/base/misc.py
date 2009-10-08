#******************************************************************************
# (C) 2009 Ableton AG
# author: Stephan Diehl (std)
# email: stephan.diehl@ableton.com
#******************************************************************************

#============================================================================
# Helper Classes

class Bunch(dict):
    def __setattr__(self, key, item):
        self[key] = item

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError

    def __delattr__(self, key):
        try:
            del self[key]
        except KeyError:
            raise AttributeError

    def copy(self):
        return Bunch(**super(Bunch, self).copy())

    def get_prefix(self, prefix):
        other = self.__class__()
        keys = [x for x in self.keys() if x.startswith(prefix)]
        for key in keys:
            other[key] = self[key]
        return other


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

    def __exit__(self, exc_type, exc_value, exc_traceback):
        return self.close()

    def read(self, limit=-1):
        return self.handle.read(limit)

    def close(self):
        retval = self.handle.close()
        os.unlink(self.tmpfilename)
        return retval

