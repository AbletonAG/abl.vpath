#******************************************************************************
# (C) 2013 Ableton AG
#******************************************************************************


import os
import tempfile
import stat
from posixpath import join as ujoin
from unittest import TestCase
import shutil

from abl.vpath.base import URI

from .common import (
    create_file,
    os_create_file,
    load_file,
    is_on_mac,
    CleanupMemoryBeforeTestMixin,
)


class CommonFileSystemTest(CleanupMemoryBeforeTestMixin, TestCase):
    __test__ = False

    def setUp(self):
        super(CommonFileSystemTest, self).setUp()
        self.local_setup()
        self.foo_path = URI(self.baseurl) / 'foo'
        self.existing_dir = ujoin(self.baseurl, 'foo')
        self.existing_file = ujoin(self.baseurl, 'foo', 'foo.txt')
        self.non_existing_file = ujoin(self.baseurl, 'bar.txt')


    def tearDown(self):
        self.local_teardown()


    def test_file(self):
        path = URI(self.baseurl) / 'testfile.txt'
        create_file(path, content='hallo')
        content = load_file(path)

        self.assertEqual(content, 'hallo')
        self.assertTrue(path.exists())
        self.assertTrue(path.isfile())
        path.remove()
        self.assertTrue(not path.exists())

        path = URI(self.existing_file)
        self.assertTrue(path.exists())
        self.assertTrue(path.isfile())

        content = load_file(path)
        self.assertTrue(content)


    def test_dir(self):
        testdir = URI('testdir')
        testdir.makedirs()
        self.assertTrue(testdir.exists())
        self.assertTrue(testdir.isdir())
        self.assertTrue(not testdir.isfile())
        testfile = URI('testdir/somefile')
        create_file(testfile, content='test')
        testdir.remove(recursive=True)
        self.assertTrue(not testdir.exists())
        self.assertTrue(not testfile.exists())

        testdir = URI(self.existing_dir)
        self.assertTrue(testdir.exists())
        self.assertTrue(testdir.isdir())


    def test_listdir(self):
        path = URI(self.existing_dir)
        dirs = path.listdir()
        self.assertTrue('foo.txt' in dirs)


    def test_copy_and_move_file(self):
        single_file = URI(self.non_existing_file)
        target_file = URI(self.baseurl) / 'target_file.txt'
        create_file(single_file)

        single_file.copy(target_file)
        self.assertTrue(target_file.exists())
        self.assertTrue(target_file.isfile())
        self.assertEqual(load_file(target_file), 'content')

        target_file.remove()
        self.assertTrue(not target_file.exists())
        single_file.move(target_file)

        self.assertTrue(not single_file.exists())
        self.assertTrue(target_file.exists())
        self.assertTrue(target_file.isfile())

        self.assertEqual(load_file(target_file), 'content')
        target_file.remove()


    def test_copy_and_move_dir(self):
        folder = URI(self.baseurl) / 'folder'
        folder.makedirs()

        self.assertTrue(folder.isdir())
        afile = folder / 'afile.txt'
        create_file(afile)

        target = URI(self.baseurl) / 'target'
        self.assertTrue(not target.exists())
        folder.copy(target, recursive=True)
        self.assertTrue(target.exists())

        target_file = target / 'afile.txt'
        self.assertTrue(target_file.exists())
        self.assertEqual(load_file(target_file), 'content')

        target.remove(recursive=True)
        self.assertTrue(not target.exists())
        target.makedirs()
        folder.copy(target, recursive=True)

        newtarget = target / 'folder'
        self.assertTrue(newtarget.exists())
        self.assertTrue(newtarget.isdir())

        newtarget_file = newtarget / 'afile.txt'
        self.assertTrue(newtarget_file.exists())
        self.assertTrue(newtarget_file.isfile())
        target.remove(recursive=True)

        folder.move(target)
        self.assertTrue(not folder.exists())
        self.assertTrue(target.exists())
        self.assertTrue(target.isdir())
        self.assertTrue(target_file.exists())
        self.assertTrue(target_file.isfile())
        target.remove(recursive=True)


    def test_move_folder_to_subfolder(self):
        """Test moving a directory '/some/path/folder' to '/some/path/target'.
        '/some/path/target' does already exist.  It is expected that after
        the move '/some/path/target/folder' exists.
        """
        folder = self.foo_path / 'folder'
        content = folder / 'content_dir'
        and_more = content / 'and_more'
        and_more.makedirs()

        target = self.foo_path / 'target'
        target.makedirs()

        folder.move(target)

        self.assertTrue(not folder.exists())
        self.assertTrue(target.exists())
        self.assertTrue('folder' in target.listdir())
        self.assertTrue((target / 'folder').isdir())
        self.assertTrue((target / 'folder' / 'content_dir').isdir())


    def test_rename_folder(self):
        """Test moving a directory '/some/path/folder' to '/some/path/target'.
        '/some/path/target' does NOT yet exist.  It is expected that after
        the move '/some/path/target' exists and is actually the former
        '/some/path/folder'.
        """
        folder = self.foo_path / 'folder'
        content = folder / 'content_dir'
        and_more = content / 'and_more'

        and_more.makedirs()

        target = self.foo_path / 'target'
        folder.move(target)

        self.assertTrue(not folder.exists())
        self.assertTrue(target.isdir())
        self.assertTrue('content_dir' in target.listdir())


    def test_copy_recursive_with_preservelinks(self):
        src_path = URI(self.baseurl) / 'folder'
        base_path = src_path / 'gaz'
        foo_path = base_path / 'foo'
        bar_path = foo_path / 'tmp'
        bar_path.makedirs()

        mee_path = foo_path / 'mee.txt'
        create_file(mee_path)
        mee2_path = bar_path / 'mee2.txt'
        create_file(mee2_path)

        dest_path = URI(self.baseurl) / 'helloworld'

        src_path.copy(dest_path, recursive=True, followlinks=False)

        self.assertTrue((dest_path / 'gaz' / 'foo' / 'mee.txt').isfile())
        self.assertTrue((dest_path / 'gaz' / 'foo' / 'tmp').isdir())


    def test_remove_recursive_with_readonly_file(self):
        foo_path = URI(self.baseurl) / 'foo'
        bar_path = foo_path / 'bar'
        bar_path.makedirs()

        gaz_path = bar_path / 'ghaz.txt'
        create_file(gaz_path)

        mode = gaz_path.info().mode
        gaz_path.info(set_info=dict(mode=mode & ~stat.S_IWUSR))

        foo_path.remove(recursive=True)

        self.assertTrue(not foo_path.exists())


    #------------------------------

    def test_open_unknown_file_fails(self):
        """Check that both backends fail with a proper exception when trying to
        open a path for loading, which does not exist.
        """
        root = URI(self.baseurl)
        notexisting_path = root / 'ma' / 'moo'
        self.assertRaises(IOError, load_file, notexisting_path)
        self.assertRaises(IOError, create_file, notexisting_path)


class TestLocalFileSystem(CommonFileSystemTest):
    __test__ = True

    def local_setup(self):
        thisdir = os.path.split(os.path.abspath(__file__))[0]
        self.tmpdir = tempfile.mkdtemp('.temp', 'test-local-fs', thisdir)
        self.baseurl = 'file://' + self.tmpdir

        foo_dir = os.path.join(self.tmpdir, 'foo')
        bar_dir = os.path.join(foo_dir, 'bar')
        os.makedirs(foo_dir)
        os.makedirs(bar_dir)

        some_file = os.path.join(foo_dir, 'foo.txt')
        os_create_file(some_file)


    def local_teardown(self):
        shutil.rmtree(self.tmpdir)



class TestMemoryFileSystem(CommonFileSystemTest):
    __test__ = True

    def local_setup(self):
        self.baseurl = "memory:///"

        foo_path = URI(self.baseurl) / 'foo'
        bar_path = foo_path / 'bar'
        bar_path.makedirs()

        some_path = foo_path / 'foo.txt'
        create_file(some_path)


    def local_teardown(self):
        pass


#-------------------------------------------------------------------------------

class CommonFSCopyTest(TestCase):
    __test__ = False

    def test_copystat_exec_to_nonexec(self):
        root = URI(self.baseurl)

        # create a file with execution flag
        xfile = create_file(root / 'xfile.exe')
        xfile.set_exec(stat.S_IXUSR)

        # create a file without exec flag
        ofile = create_file(root / 'otherfile.exe')

        xfile.copystat(ofile)

        self.assertTrue(ofile.isexec())


    def test_copystat_nonexec_to_exec(self):
        root = URI(self.baseurl)

        # create a file with execution flag
        xfile = create_file(root / 'xfile.sh')
        xfile.set_exec(stat.S_IXUSR)

        # create a file without exec flag
        ofile = create_file(root / 'otherfile.txt')

        ofile.copystat(xfile)

        self.assertTrue(not xfile.isexec())


    def test_copy_recursive(self):
        root = URI(self.baseurl)
        foo_path = root / 'foo'
        foo_path.mkdir()

        bar_path = root / 'bar'

        # create a file with execution flag
        xfile = create_file(foo_path / 'xfile.exe')
        xfile.set_exec(stat.S_IXUSR)

        zfile = create_file(foo_path / 'zfile.exe')
        zfile.set_exec(stat.S_IXUSR)

        # create a file without exec flag
        create_file(foo_path / 'otherfile.txt')
        create_file(foo_path / 'nfile.txt')

        foo_path.copy(bar_path, recursive=True)

        self.assertTrue((bar_path / 'xfile.exe').isexec())
        self.assertTrue((bar_path / 'zfile.exe').isexec())
        self.assertTrue(not (bar_path / 'otherfile.txt').isexec())
        self.assertTrue(not (bar_path / 'nfile.txt').isexec())


    def test_copy_dir_to_file(self):
        root = URI(self.baseurl)
        bar_path = root / 'foo' / 'bar'
        bar_path.makedirs()
        gaz_path = bar_path / 'gaz.txt'
        create_file(gaz_path, content='foobar')

        moo_path = root / 'moo.txt'
        create_file(moo_path, content='moomoo')

        # can't copy dir on (existing) file
        self.assertRaises(OSError, bar_path.copy,
                              moo_path, recursive=True)


    def test_copy_empty_dirs_recursive(self):
        root = URI(self.baseurl)
        root.makedirs()

        gaz_path = root / 'gaz'
        gaz_path.makedirs()

        moo_path = root / 'moo'

        gaz_path.copy(moo_path, recursive=True)

        self.assertTrue((moo_path).isdir())


class TestLocalFSCopy2(CommonFSCopyTest):
    __test__ = True

    def setUp(self):
        thisdir = os.path.split(os.path.abspath(__file__))[0]
        self.tmpdir = tempfile.mkdtemp('.temp', 'test-local-fs', thisdir)
        self.baseurl = 'file://' + self.tmpdir

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


class TestMemoryFSCopy2(CleanupMemoryBeforeTestMixin, CommonFSCopyTest):
    __test__ = True

    def setUp(self):
        super(TestMemoryFSCopy2, self).setUp()
        self.baseurl = "memory:///"

    def tearDown(self):
        pass


#-------------------------------------------------------------------------------

class CommonFSExecTest(TestCase):
    __test__ = False

    def test_exec_flags(self):
        root = URI(self.baseurl)

        # create a file with execution flag
        xfile = create_file(root / 'xfile.exe')

        xfile.set_exec(stat.S_IXUSR)
        self.assertTrue(xfile.isexec())
        self.assertEqual(xfile.info().mode & stat.S_IXUSR, stat.S_IXUSR)

        # create a file without exec flag
        ofile = create_file(root / 'otherfile.txt')

        self.assertEqual(ofile.info().mode & stat.S_IXUSR, 0)
        self.assertTrue(not ofile.isexec())


class TestLocalFSExec(CommonFSExecTest):
    __test__ = True

    def setUp(self):
        thisdir = os.path.split(os.path.abspath(__file__))[0]
        self.tmpdir = tempfile.mkdtemp('.temp', 'test-local-fs', thisdir)
        self.baseurl = 'file://' + self.tmpdir

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


class TestMemoryFSExec(CleanupMemoryBeforeTestMixin, CommonFSExecTest):
    __test__ = True

    def setUp(self):
        super(TestMemoryFSExec, self).setUp()
        self.baseurl = "memory:///"

    def tearDown(self):
        pass


#-------------------------------------------------------------------------------

class CommonLocalFSSymlinkTest(TestCase):
    __test__ = False

    def test_symlink_dir(self):
        root = URI(self.baseurl)
        bar_path = root / 'foo' / 'bar'
        bar_path.makedirs()

        create_file(bar_path / 'gaz.txt')

        moo_path = root / 'moo'

        self.assertTrue(not moo_path.exists())
        self.assertTrue(not moo_path.islink())

        bar_path.symlink(moo_path)

        self.assertTrue(moo_path.exists())
        self.assertTrue(moo_path.islink())
        # a symlink to a dir is a dir
        self.assertTrue(moo_path.isdir())

        link = moo_path.readlink()
        self.assertEqual(link, bar_path)

        # check that gaz.txt is accessible through the symlink
        self.assertTrue(moo_path / 'gaz.txt')


    def test_symlink_file(self):
        root = URI(self.baseurl)
        bar_path = root / 'foo' / 'bar'
        bar_path.makedirs()

        gaz_path = bar_path / 'gaz.txt'
        create_file(gaz_path, content='foobar')

        tee_path = root / 'helloworld'

        self.assertTrue(not tee_path.exists())
        self.assertTrue(not tee_path.islink())

        gaz_path.symlink(tee_path)

        self.assertTrue(tee_path.exists())
        self.assertTrue(tee_path.islink())
        # a symlink to a file is a file
        self.assertTrue(tee_path.isfile())

        link = tee_path.readlink()
        self.assertEqual(link, gaz_path)

        # check that gaz.txt is accessible through the symlink
        self.assertEqual(load_file(tee_path), 'foobar')


    #------------------------------

    def test_symlink_on_unknown_file(self):
        """Check that backends fail with a proper exception when trying to
        create a symlink on a path where directory steps do not exist.
        """
        root = URI(self.baseurl)
        notexisting_path = root / 'ma' / 'moo'
        tee_path = root / 'helloworld'
        notexisting_path.symlink(tee_path)

        self.assertTrue(tee_path.islink())
        self.assertEqual(tee_path.readlink(), notexisting_path)
        self.assertTrue(not notexisting_path.exists())


    def test_open_deadlink_fails(self):
        root = URI(self.baseurl)

        notexisting_path = root / 'foo' / 'bar'
        tee_path = root / 'helloworld'
        notexisting_path.symlink(tee_path)

        self.assertRaises(IOError, load_file, tee_path)
        self.assertRaises(IOError, create_file, tee_path)


    def test_listdir_deadlink_fails(self):
        root = URI(self.baseurl)

        notexisting_path = root / 'foo' / 'bar'
        tee_path = root / 'helloworld'
        notexisting_path.symlink(tee_path)

        self.assertRaises(OSError, tee_path.listdir)


    def test_isfile_doesnt_fail_on_deadlink(self):
        root = URI(self.baseurl)

        notexisting_path = root / 'foo' / 'bar'
        tee_path = root / 'helloworld'
        notexisting_path.symlink(tee_path)

        self.assertTrue(not tee_path.isfile())
        self.assertTrue(not tee_path.isdir())
        self.assertTrue(not tee_path.exists())


    def test_isdir_doesnt_fail_on_deadlink(self):
        root = URI(self.baseurl)

        notexisting_path = root / 'foo' / 'bar'
        tee_path = root / 'helloworld'
        notexisting_path.symlink(tee_path)

        self.assertTrue(not tee_path.isdir())


    def test_exists_doesnt_fail_on_deadlink(self):
        root = URI(self.baseurl)

        notexisting_path = root / 'foo' / 'bar'
        tee_path = root / 'helloworld'
        notexisting_path.symlink(tee_path)

        self.assertTrue(not tee_path.exists())


    def test_isexec_fails_on_deadlink(self):
        root = URI(self.baseurl)

        notexisting_path = root / 'foo' / 'bar'
        tee_path = root / 'helloworld'
        notexisting_path.symlink(tee_path)

        self.assertRaises(OSError, tee_path.isexec)


    def test_set_exec_fails_on_deadlink(self):
        root = URI(self.baseurl)

        notexisting_path = root / 'foo' / 'bar'
        tee_path = root / 'helloworld'
        notexisting_path.symlink(tee_path)

        self.assertRaises(OSError, tee_path.set_exec,
                              stat.S_IXUSR | stat.S_IXGRP)


class TestLocalFSSymlink(CommonLocalFSSymlinkTest):
    __test__ = is_on_mac()

    def setUp(self):
        self.thisdir = os.path.split(os.path.abspath(__file__))[0]
        self.tmpdir = tempfile.mkdtemp('.temp', 'test-local-fs', self.thisdir)
        self.baseurl = 'file://' + self.tmpdir


    def tearDown(self):
        shutil.rmtree(self.tmpdir)


class TestMemoryFSSymlink(CleanupMemoryBeforeTestMixin, CommonLocalFSSymlinkTest):
    __test__ = True

    def setUp(self):
        super(TestMemoryFSSymlink, self).setUp()
        self.baseurl = "memory:///"

    def tearDown(self):
        pass
