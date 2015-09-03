#******************************************************************************
# (C) 2013 Ableton AG
#******************************************************************************

from __future__ import with_statement
import os
import tempfile
import shutil
from unittest import TestCase

from abl.vpath.base import *

from .common import (
    create_file,
    load_file,
    is_on_mac,
    CleanupMemoryBeforeTestMixin,
)


#-------------------------------------------------------------------------------

class CommonLocalFSSymlinkCopyTest(TestCase):
    __test__ = False

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
        self.assert_((bar_path / 'gaz2.txt').isfile())
        self.assert_((bar_path / 'gaz.txt').isfile())


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


    #------------------------------

    def test_copy_dirsymlink_to_file_followlinks(self):
        root = URI(self.baseurl)
        bar_path = root / 'foo' / 'bar'
        bar_path.makedirs()
        gaz_path = bar_path / 'gaz.txt'
        create_file(gaz_path, content='foobar')

        tee_path = root / 'helloworld'
        bar_path.symlink(tee_path)

        moo_path = root / 'moo.txt'
        create_file(moo_path, content='moomoo')

        # can't copy dir over existing file
        self.failUnlessRaises(OSError, tee_path.copy, moo_path,
                              recursive=True, followlinks=True)


    def test_copy_dirsymlink_to_file_preservelinks(self):
        root = URI(self.baseurl)
        bar_path = root / 'foo' / 'bar'
        bar_path.makedirs()
        gaz_path = bar_path / 'gaz.txt'
        create_file(gaz_path, content='foobar')

        tee_path = root / 'helloworld'
        bar_path.symlink(tee_path)

        moo_path = root / 'moo.txt'
        create_file(moo_path, content='moomoo')

        tee_path.copy(moo_path, recursive=True, followlinks=False)

        self.assert_(moo_path.islink())
        self.assert_(moo_path.isdir())
        self.assert_(load_file(moo_path / 'gaz.txt') == 'foobar')


    def test_copy_dirsymlink_to_dir_followlinks(self):
        root = URI(self.baseurl)
        bar_path = root / 'foo' / 'bar'
        bar_path.makedirs()
        gaz_path = bar_path / 'gaz.txt'
        create_file(gaz_path, content='foobar')

        tee_path = root / 'helloworld'
        bar_path.symlink(tee_path)

        moo_path = root / 'moo'
        moo_path.makedirs()

        # can't copy dir over existing file
        tee_path.copy(moo_path, recursive=True, followlinks=True)

        helloworld_path = moo_path / 'helloworld'
        self.assert_(not helloworld_path.islink())
        self.assert_(helloworld_path.isdir())
        self.assert_((helloworld_path / 'gaz.txt').isfile())


    def test_copy_dirsymlink_to_dir_preservelinks(self):
        root = URI(self.baseurl)
        bar_path = root / 'foo' / 'bar'
        bar_path.makedirs()
        gaz_path = bar_path / 'gaz.txt'
        create_file(gaz_path, content='foobar')

        tee_path = root / 'helloworld'
        bar_path.symlink(tee_path)

        moo_path = root / 'moo'
        moo_path.makedirs()

        # can't copy dir over existing file
        tee_path.copy(moo_path, recursive=True, followlinks=False)

        helloworld_path = moo_path / 'helloworld'
        self.assert_(helloworld_path.islink())
        self.assert_(helloworld_path.isdir())
        self.assert_(helloworld_path.readlink() == bar_path)


    def test_copy_dirsymlink_to_missingfile_followlinks(self):
        root = URI(self.baseurl)
        bar_path = root / 'foo' / 'bar'
        bar_path.makedirs()
        gaz_path = bar_path / 'gaz.txt'
        create_file(gaz_path, content='foobar')

        tee_path = root / 'helloworld'
        bar_path.symlink(tee_path)

        moo_path = root / 'moo'

        # can't copy dir over existing file
        tee_path.copy(moo_path, recursive=True, followlinks=True)

        self.assert_(not moo_path.islink())
        self.assert_(moo_path.isdir())
        self.assert_((moo_path / 'gaz.txt').isfile())


    def test_copy_dirsymlink_to_missingfile_preservelinks(self):
        root = URI(self.baseurl)
        bar_path = root / 'foo' / 'bar'
        bar_path.makedirs()
        gaz_path = bar_path / 'gaz.txt'
        create_file(gaz_path, content='foobar')

        tee_path = root / 'helloworld'
        bar_path.symlink(tee_path)

        moo_path = root / 'moo'

        # can't copy dir over existing file
        tee_path.copy(moo_path, recursive=True, followlinks=False)

        self.assert_(moo_path.islink())
        self.assert_(moo_path.isdir())
        self.assert_(moo_path.readlink() == bar_path)


    def test_copy_dirsymlink_to_filesymlink_followlinks(self):
        root = URI(self.baseurl)
        bar_path = root / 'foo' / 'bar'
        bar_path.makedirs()

        gaz_path = bar_path / 'gaz.txt'
        create_file(gaz_path, content='foobar')

        gaz2_path = bar_path / 'gaz2.txt'
        create_file(gaz2_path, content='foobar2')

        tee_path = root / 'helloworld'
        bar_path.symlink(tee_path)

        tee2_path = root / 'helloworld2'
        gaz2_path.symlink(tee2_path)

        # copying a dir to a symlink->file fails.
        self.failUnlessRaises(OSError, tee_path.copy,
                              tee2_path, recursive=True, followlinks=True)


    def test_copy_dirsymlink_to_filesymlink_preservelinks(self):
        root = URI(self.baseurl)
        bar_path = root / 'foo' / 'bar'
        bar_path.makedirs()

        gaz_path = bar_path / 'gaz.txt'
        create_file(gaz_path, content='foobar')

        gaz2_path = bar_path / 'gaz2.txt'
        create_file(gaz2_path, content='foobar2')

        tee_path = root / 'helloworld'
        bar_path.symlink(tee_path)

        tee2_path = root / 'helloworld2'
        gaz2_path.symlink(tee2_path)

        # copying a dir to a symlink->file fails.
        tee_path.copy(tee2_path, recursive=True, followlinks=False)

        self.assert_(tee2_path.islink())
        self.assert_(tee2_path.isdir())
        self.assert_(tee2_path.readlink() == tee_path.readlink())
        self.assert_(tee2_path.readlink() == bar_path)


    def test_copy_dirsymlink_to_dirsymlink_followlinks(self):
        root = URI(self.baseurl)
        bar_path = root / 'foo' / 'bar'
        bar_path.makedirs()

        gaz_path = bar_path / 'gaz.txt'
        create_file(gaz_path, content='foobar')

        moo_path = root / 'moo'
        moo_path.makedirs()

        tee_path = root / 'helloworld'
        bar_path.symlink(tee_path)

        tee2_path = root / 'helloworld2'
        moo_path.symlink(tee2_path)

        tee_path.copy(tee2_path, recursive=True, followlinks=True)

        helloworld_path = tee2_path / 'helloworld'

        self.assert_(tee2_path.islink())  # still a link?
        self.assert_(tee_path.islink())  # still a link?

        self.assert_(not helloworld_path.islink())
        self.assert_(helloworld_path.isdir())
        self.assert_((helloworld_path / 'gaz.txt').isfile())


    def test_copy_dirsymlink_to_dirsymlink_preservelinks(self):
        root = URI(self.baseurl)
        bar_path = root / 'foo' / 'bar'
        bar_path.makedirs()

        gaz_path = bar_path / 'gaz.txt'
        create_file(gaz_path, content='foobar')

        moo_path = root / 'moo'
        moo_path.makedirs()

        tee_path = root / 'helloworld'
        bar_path.symlink(tee_path)

        tee2_path = root / 'helloworld2'
        moo_path.symlink(tee2_path)

        tee_path.copy(tee2_path, recursive=True, followlinks=False)

        helloworld_path = tee2_path / 'helloworld'

        self.assert_(tee2_path.islink())  # still a link?
        self.assert_(tee_path.islink())  # still a link?

        self.assert_(helloworld_path.islink())
        self.assert_(helloworld_path.isdir())
        self.assert_((helloworld_path / 'gaz.txt').isfile())
        self.assert_(helloworld_path.readlink() == bar_path)
        self.assert_(helloworld_path.readlink() == tee_path.readlink())



class TestLocalFSSymlinkCopy(CommonLocalFSSymlinkCopyTest):
    __test__ = is_on_mac()

    def setUp(self):
        self.thisdir = os.path.split(os.path.abspath(__file__))[0]
        self.tmpdir = tempfile.mkdtemp('.temp', 'test-local-fs', self.thisdir)
        self.baseurl = 'file://' + self.tmpdir


    def tearDown(self):
        shutil.rmtree(self.tmpdir)


class TestMemoryFSSymlinkCopy(CleanupMemoryBeforeTestMixin, CommonLocalFSSymlinkCopyTest):
    __test__ = True

    def setUp(self):
        super(TestMemoryFSSymlinkCopy, self).setUp()
        self.baseurl = "memory:///"

    def tearDown(self):
        pass
