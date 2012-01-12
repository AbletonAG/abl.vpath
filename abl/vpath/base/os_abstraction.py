"""
This module abstracts away the os-module
so that we can use posix/windows specific
functionality.

Also, pywin32 currently is not shipped 
Ableton Live's builtin Python, so we rewire
calls to win32 through a different module.
"""
import platform

if platform.system() in ('Windows', 'Microsoft'):
    import os as builtin_os
    import win32api
    import win32con
    import pywintypes
    pywinerror = pywintypes.error

    class os(object):

        @classmethod
        def unlink(cls, pth):
            try:
                return builtin_os.unlink(pth)
            except WindowsError:
                win32api.SetFileAttributes(pth, win32con.FILE_ATTRIBUTE_NORMAL)
                return builtin_os.unlink(pth)


        @classmethod
        def listdir(cls, pth):
            return builtin_os.listdir(pth)


        @classmethod
        def mkdir(cls, pth):
            return builtin_os.mkdir(pth)


        @classmethod
        def stat(cls, pth):
            return builtin_os.stat(pth)


        @classmethod
        def rmdir(cls, pth):
            try:
                return builtin_os.rmdir(pth)
            except WindowsError:
                win32api.SetFileAttributes(pth, win32con.FILE_ATTRIBUTE_NORMAL)
                return builtin_os.rmdir(pth)

        # the path-submodule
        path = builtin_os.path
else:
    import os


