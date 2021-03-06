#******************************************************************************
# (C) 2013 Ableton AG
#******************************************************************************


import os
import tempfile
from unittest import TestCase
import shutil
from abl.vpath.base import URI

from .common import (
    create_file,
    is_on_mac,
    CleanupMemoryBeforeTestMixin,
)


#-------------------------------------------------------------------------------

class CommonLocalFSSymlinkRemoveTest(TestCase):
    __test__ = False

    def test_remove_recursive_with_symlinks(self):
        root = URI(self.baseurl)
        hw_path = root / 'doo' / 'helloworld'
        hw_path.makedirs()
        humpty_path = hw_path / 'humpty.txt'
        create_file(humpty_path)

        raz_path = root / 'raz'
        mam_path = raz_path / 'mam'
        mam_path.makedirs()
        create_file(mam_path / 'x')

        foo_path = root / 'foo'
        bar_path = foo_path / 'bar'
        bar_path.makedirs()

        gaz_path = bar_path / 'gaz.txt'
        create_file(gaz_path, content='foobar')

        # a symlink to a dir outside of foo
        tee_path = bar_path / 'tee'
        mam_path.symlink(tee_path)

        # a symlink to a file outside of foo
        moo_path = bar_path / 'moo.txt'
        humpty_path.symlink(moo_path)

        foo_path.remove(recursive=True)

        self.assertTrue(not foo_path.isdir())

        # followlinks: the pointed to files should not been deleted
        self.assertTrue(humpty_path.isfile())
        self.assertTrue(mam_path.isdir())
        self.assertTrue(raz_path.isdir())


    def test_remove_symlink_to_file(self):
        root = URI(self.baseurl)
        humpty_path = root / 'humpty.txt'
        create_file(humpty_path)

        foo_path = root / 'foo.txt'
        humpty_path.symlink(foo_path)

        foo_path.remove()

        self.assertTrue(humpty_path.isfile())


    def test_remove_symlink_to_looped_symlink(self):
        root = URI(self.baseurl)
        humpty_path = root / 'humpty.txt'
        humpty_path.symlink(humpty_path)

        foo_path = root / 'foo.txt'
        humpty_path.symlink(foo_path)

        foo_path.remove()

        self.assertTrue(humpty_path.islink())




class TestLocalFSSymlinkRemove(CommonLocalFSSymlinkRemoveTest):
    __test__ = is_on_mac()

    def setUp(self):
        self.thisdir = os.path.split(os.path.abspath(__file__))[0]
        self.tmpdir = tempfile.mkdtemp('.temp', 'test-local-fs', self.thisdir)
        self.baseurl = 'file://' + self.tmpdir


    def tearDown(self):
        shutil.rmtree(self.tmpdir)


class TestMemoryFSSymlinkRemove(CleanupMemoryBeforeTestMixin, CommonLocalFSSymlinkRemoveTest):
    __test__ = True

    def setUp(self):
        super(TestMemoryFSSymlinkRemove, self).setUp()
        self.baseurl = "memory:///"

    def tearDown(self):
        pass
