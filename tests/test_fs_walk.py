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
    mac_only,
    CleanupMemoryBeforeTestMixin,
)


class CommonFileSystemWalkTest(TestCase):
    __test__ = False


    def _walk(self, base_path, *args, **kwargs):
        actual = []
        base_path_len = len(base_path.path)
        for dirname, dirs, files in base_path.walk(*args, **kwargs):
            relpath = '.%s' % dirname.path[base_path_len:].replace('\\', '/')
            actual.append("ROOT: %s" % relpath)
            for name in files:
                actual.append('FILE: %s' % name)
            for name in dirs:
                actual.append('DIR: %s' % name)
        return actual


    def _setup_hierarchy(self):
        """Walk the following tree:
           foo/
             test.py
             bar/
               file1a.txt
               file1b.png
             gaz/
             file2a.jpg
             file2b.html
        """

        path = URI(self.baseurl)
        foo_path = path / 'foo'
        bar_path = foo_path / 'bar'
        bar_path.makedirs()
        gaz_path = foo_path / 'gaz'
        gaz_path.makedirs()

        create_file(bar_path / 'file1a.txt')
        create_file(bar_path / 'file1b.png')
        create_file(foo_path / 'file2a.jpg')
        create_file(foo_path / 'file2b.html')
        create_file(foo_path / 'test.py')

        return foo_path


    def test_walk_topdown(self):
        foo_path = self._setup_hierarchy()

        actual = self._walk(foo_path, topdown=True, followlinks=True)

        expected = [
            'ROOT: .',
            'FILE: file2a.jpg',
            'FILE: file2b.html',
            'FILE: test.py',
            'DIR: bar',
            'DIR: gaz',
            'ROOT: ./bar',
            'FILE: file1a.txt',
            'FILE: file1b.png',
            'ROOT: ./gaz',
            ]

        self.assertEqual(expected, actual)


    def test_walk_bottomup(self):
        foo_path = self._setup_hierarchy()

        actual = self._walk(foo_path, topdown=False, followlinks=True)

        expected = [
            'ROOT: ./bar',
            'FILE: file1a.txt',
            'FILE: file1b.png',
            'ROOT: ./gaz',
            'ROOT: .',
            'FILE: file2a.jpg',
            'FILE: file2b.html',
            'FILE: test.py',
            'DIR: bar',
            'DIR: gaz',
            ]

        self.assertEqual(expected, actual)


    #--------------------------------------------------------------------------

    def _setup_hierarchy_with_symlink(self, withloop=None, withbrokenlink=False):
        """Walk the following tree:
           foo/
             test.py
             bar/
               file1a.txt
               file1b.png
               humpty -> raz
             gaz/
             file2a.jpg
             file2b.html

           raz/
             moo/
               test1.sh
             test2.sh
        """

        path = URI(self.baseurl)
        foo_path = path / 'foo'
        bar_path = foo_path / 'bar'
        bar_path.makedirs()
        gaz_path = foo_path / 'gaz'
        gaz_path.makedirs()

        create_file(bar_path / 'file1a.txt')
        create_file(bar_path / 'file1b.png')
        create_file(foo_path / 'file2a.jpg')
        create_file(foo_path / 'file2b.html')
        create_file(foo_path / 'test.py')


        raz_path = path / 'raz'
        moo_path = raz_path / 'moo'
        moo_path.makedirs()

        create_file(moo_path / 'test1.sh')
        create_file(raz_path / 'test2.sh')

        raz_path.symlink(bar_path / 'humpty')

        if withloop == 'Dir':
            foo_path.symlink(moo_path / 'back_to_foo')
        elif withloop == 'file':
            dumpty_path = bar_path / 'dumpty'
            dumpty_path.symlink(dumpty_path)

        if withbrokenlink:
            ixw_path = bar_path / 'dumpty'
            (foo_path / 'nowhere_in_particular').symlink(ixw_path)

        return foo_path


    @mac_only
    def test_walk_topdown_follow_symlinks(self):
        foo_path = self._setup_hierarchy_with_symlink()

        actual = self._walk(foo_path, topdown=True, followlinks=True)

        expected = [
            'ROOT: .',
            'FILE: file2a.jpg',
            'FILE: file2b.html',
            'FILE: test.py',
            'DIR: bar',
            'DIR: gaz',
            'ROOT: ./bar',
            'FILE: file1a.txt',
            'FILE: file1b.png',
            'DIR: humpty',
            'ROOT: ./bar/humpty',
            'FILE: test2.sh',
            'DIR: moo',
            'ROOT: ./bar/humpty/moo',
            'FILE: test1.sh',
            'ROOT: ./gaz',
            ]

        self.assertEqual(expected, actual)


    @mac_only
    def test_walk_topdown_dont_follow_symlinks(self):
        foo_path = self._setup_hierarchy_with_symlink()

        actual = self._walk(foo_path, topdown=True, followlinks=False)

        expected = [
            'ROOT: .',
            'FILE: file2a.jpg',
            'FILE: file2b.html',
            'FILE: test.py',
            'DIR: bar',
            'DIR: gaz',
            'ROOT: ./bar',
            'FILE: file1a.txt',
            'FILE: file1b.png',
            'DIR: humpty',
            'ROOT: ./gaz',
            ]

        self.assertEqual(expected, actual)


    @mac_only
    def test_walk_bottomup_follow_symlinks(self):
        foo_path = self._setup_hierarchy_with_symlink()

        actual = self._walk(foo_path, topdown=False, followlinks=True)

        expected = [
            'ROOT: ./bar/humpty/moo',
            'FILE: test1.sh',
            'ROOT: ./bar/humpty',
            'FILE: test2.sh',
            'DIR: moo',
            'ROOT: ./bar',
            'FILE: file1a.txt',
            'FILE: file1b.png',
            'DIR: humpty',
            'ROOT: ./gaz',
            'ROOT: .',
            'FILE: file2a.jpg',
            'FILE: file2b.html',
            'FILE: test.py',
            'DIR: bar',
            'DIR: gaz',
            ]

        self.assertEqual(expected, actual)


    @mac_only
    def test_walk_bottomup_dont_follow_symlinks(self):
        foo_path = self._setup_hierarchy_with_symlink()

        actual = self._walk(foo_path, topdown=False, followlinks=False)

        expected = [
            'ROOT: ./bar',
            'FILE: file1a.txt',
            'FILE: file1b.png',
            'DIR: humpty',
            'ROOT: ./gaz',
            'ROOT: .',
            'FILE: file2a.jpg',
            'FILE: file2b.html',
            'FILE: test.py',
            'DIR: bar',
            'DIR: gaz',
            ]

        self.assertEqual(expected, actual)


    #---------------------------------------------------------------------------

    # can't test behaviour of walk on followlinks with symlink loop across
    # multiple folders.  os.walk has undefined behaviour here, and so has
    # abl.vpath.walk.  os.walk will eventual stop after some time, and so
    # does localfs of abl.vpath.  memoryfs stops, but with an unrelated
    # exception.
    #
    # Since we can't rely on os.walk's behaviour we should fix abl.vpath to
    # do proper cycle detection, which is a different story though.

#    def test_walk_topdown_follow_symlinks_breaks_on_loop(self):
#        foo_path = self._setup_hierarchy_with_symlink(withloop='Dir')
#
#        actual = self._walk(foo_path, topdown=True, followlinks=True)
#
#        self.failUnlessRaises(OSError, self._walk, foo_path, topdown=True, followlinks=True)

    @mac_only
    def test_walk_topdown_follow_symlinks_wont_break_on_fileloop(self):
        foo_path = self._setup_hierarchy_with_symlink(withloop='file')

        actual = self._walk(foo_path, topdown=True, followlinks=True)

        expected = [
            'ROOT: .',
            'FILE: file2a.jpg',
            'FILE: file2b.html',
            'FILE: test.py',
            'DIR: bar',
            'DIR: gaz',
            'ROOT: ./bar',
            'FILE: dumpty',      # a loop link is reported as a file
            'FILE: file1a.txt',
            'FILE: file1b.png',
            'DIR: humpty',
            'ROOT: ./bar/humpty',
            'FILE: test2.sh',
            'DIR: moo',
            'ROOT: ./bar/humpty/moo',
            'FILE: test1.sh',
            'ROOT: ./gaz',
            ]

        self.assertEqual(expected, actual)


    @mac_only
    def test_walk_topdown_dont_follow_symlinks_wont_break_on_loop(self):
        foo_path = self._setup_hierarchy_with_symlink(withloop='Dir')

        actual = self._walk(foo_path, topdown=True, followlinks=False)

        expected = [
            'ROOT: .',
            'FILE: file2a.jpg',
            'FILE: file2b.html',
            'FILE: test.py',
            'DIR: bar',
            'DIR: gaz',
            'ROOT: ./bar',
            'FILE: file1a.txt',
            'FILE: file1b.png',
            'DIR: humpty',
            'ROOT: ./gaz',
            ]

        self.assertEqual(expected, actual)


    @mac_only
    def test_walk_topdown_dont_follow_symlinks_wont_break_on_loop_file(self):
        foo_path = self._setup_hierarchy_with_symlink(withloop='file')

        actual = self._walk(foo_path, topdown=True, followlinks=False)

        expected = [
            'ROOT: .',
            'FILE: file2a.jpg',
            'FILE: file2b.html',
            'FILE: test.py',
            'DIR: bar',
            'DIR: gaz',
            'ROOT: ./bar',
            'FILE: dumpty',    # a self loop link is reported as a file
            'FILE: file1a.txt',
            'FILE: file1b.png',
            'DIR: humpty',
            'ROOT: ./gaz',
            ]

        self.assertEqual(expected, actual)


    @mac_only
    def test_walk_topdown_follow_symlinks_wont_break_on_brokenlink(self):
        foo_path = self._setup_hierarchy_with_symlink(withbrokenlink=True)

        actual = self._walk(foo_path, topdown=True, followlinks=True)

        expected = [
            'ROOT: .',
            'FILE: file2a.jpg',
            'FILE: file2b.html',
            'FILE: test.py',
            'DIR: bar',
            'DIR: gaz',
            'ROOT: ./bar',
            'FILE: dumpty',      # a broken link is reported as a file
            'FILE: file1a.txt',
            'FILE: file1b.png',
            'DIR: humpty',
            'ROOT: ./bar/humpty',
            'FILE: test2.sh',
            'DIR: moo',
            'ROOT: ./bar/humpty/moo',
            'FILE: test1.sh',
            'ROOT: ./gaz',
            ]

        self.assertEqual(expected, actual)


    @mac_only
    def test_walk_topdown_dont_follow_symlinks_wont_break_on_brokenlink(self):
        foo_path = self._setup_hierarchy_with_symlink(withbrokenlink=True)

        actual = self._walk(foo_path, topdown=True, followlinks=False)

        expected = [
            'ROOT: .',
            'FILE: file2a.jpg',
            'FILE: file2b.html',
            'FILE: test.py',
            'DIR: bar',
            'DIR: gaz',
            'ROOT: ./bar',
            'FILE: dumpty',      # a broken link is reported as a file
            'FILE: file1a.txt',
            'FILE: file1b.png',
            'DIR: humpty',
            'ROOT: ./gaz',
            ]

        self.assertEqual(expected, actual)



    @mac_only
    def test_walk_bottomup_follow_symlinks_wont_break_on_brokenlink(self):
        foo_path = self._setup_hierarchy_with_symlink(withbrokenlink=True)

        actual = self._walk(foo_path, topdown=False, followlinks=True)

        expected = [
            'ROOT: ./bar/humpty/moo',
            'FILE: test1.sh',
            'ROOT: ./bar/humpty',
            'FILE: test2.sh',
            'DIR: moo',
            'ROOT: ./bar',
            'FILE: dumpty',      # a broken link is reported as a file
            'FILE: file1a.txt',
            'FILE: file1b.png',
            'DIR: humpty',
            'ROOT: ./gaz',
            'ROOT: .',
            'FILE: file2a.jpg',
            'FILE: file2b.html',
            'FILE: test.py',
            'DIR: bar',
            'DIR: gaz',
            ]

        self.assertEqual(expected, actual)


    @mac_only
    def test_walk_bottomup_dont_follow_symlinks_wont_break_on_brokenlink(self):
        foo_path = self._setup_hierarchy_with_symlink(withbrokenlink=True)

        actual = self._walk(foo_path, topdown=False, followlinks=False)

        expected = [
            'ROOT: ./bar',
            'FILE: dumpty',      # a broken link is reported as a file
            'FILE: file1a.txt',
            'FILE: file1b.png',
            'DIR: humpty',
            'ROOT: ./gaz',
            'ROOT: .',
            'FILE: file2a.jpg',
            'FILE: file2b.html',
            'FILE: test.py',
            'DIR: bar',
            'DIR: gaz',
            ]

        self.assertEqual(expected, actual)


    #--------------------------------------------------------------------------

    def test_walk_very_deep_hierarchies(self):
        root = URI(self.baseurl)
        foo_path = root / 'foo'
        expected = []

        def expected_root_str(path):
            return 'ROOT: .%s' % path.path[len(foo_path.path):].replace('\\', '/')

        d_path = foo_path
        for i in range(0, 49):
            nm = 'f%d' % i
            expected.append('DIR: %s' % nm)
            expected.append(expected_root_str(d_path))
            d_path = d_path / nm
        d_path.makedirs()

        expected.append(expected_root_str(d_path))

        expected.reverse()

        actual = self._walk(foo_path, topdown=False, followlinks=False)

        self.assertEqual(expected, actual)
        # expect the right amount of output.  For 64 level with 2 lines per
        # level (1 x ROOT:, 1x DIR:) + 1 for the iinermost ('f63')
        self.assertEqual(len(actual), 99)


class TestLocalFSSymlinkWalk(CommonFileSystemWalkTest):
    __test__ = True

    def setUp(self):
        self.thisdir = os.path.split(os.path.abspath(__file__))[0]
        self.tmpdir = tempfile.mkdtemp('.temp', 'test-local-fs', self.thisdir)
        self.baseurl = 'file://' + self.tmpdir


    def tearDown(self):
        shutil.rmtree(self.tmpdir)


class TestMemoryFSSymlinkWalk(CleanupMemoryBeforeTestMixin, CommonFileSystemWalkTest):
    __test__ = True

    def setUp(self):
        super(TestMemoryFSSymlinkWalk, self).setUp()
        self.baseurl = "memory:///"

    def tearDown(self):
        pass
