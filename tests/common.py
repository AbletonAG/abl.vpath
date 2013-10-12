#******************************************************************************
# (C) 2013 Ableton AG
#******************************************************************************

from __future__ import with_statement
import sys
from functools import wraps
from abl.vpath.base import *


def create_file(path, content='content'):
    with path.open('w') as fs:
        fs.write(content)
    return path


def load_file(path):
    with path.open('r') as f:
        return f.read()


def mac_only(func):
    """decorator to mark test functions as mac only"""

    @wraps(func)
    def _decorator(*args, **kwargs):
        if sys.platform != "darwin":
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


