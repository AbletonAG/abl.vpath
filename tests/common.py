#******************************************************************************
# (C) 2013 Ableton AG
#******************************************************************************

from __future__ import with_statement
import sys
from functools import wraps
from abl.vpath.base.fs import CONNECTION_REGISTRY


def os_create_file(some_file, content='content'):
    with open(some_file, 'w') as fd:
        fd.write('content')


def create_file(path, content='content'):
    with path.open('w') as fs:
        fs.write(content)
    return path


def load_file(path):
    with path.open('r') as f:
        return f.read()


def is_on_mac():
    return sys.platform == "darwin"


def mac_only(func):
    """decorator to mark test functions as mac only"""

    @wraps(func)
    def _decorator(*args, **kwargs):
        if not is_on_mac():
            return
        func(*args, **kwargs)

    return _decorator


def windows_only(func):
    """decorator to mark test functions as windows only"""

    @wraps(func)
    def _decorator(*args, **kwargs):
        if sys.platform != "windows":
            return
        func(*args, **kwargs)

    return _decorator


class CleanupMemoryBeforeTestMixin(object):

    def setUp(self):
        CONNECTION_REGISTRY.cleanup(force=True)
