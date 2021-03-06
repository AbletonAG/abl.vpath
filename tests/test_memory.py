#******************************************************************************
# (C) 2008-2013 Ableton AG
#******************************************************************************



from io import StringIO
import errno
import tempfile
import time
import stat
from unittest import TestCase

from abl.util import LockFileObtainException
from abl.vpath.base import URI
from abl.vpath.base.exceptions import FileDoesNotExistError
from abl.vpath.base.fs import CONNECTION_REGISTRY

from .common import create_file, CleanupMemoryBeforeTestMixin


class MemoryFSTests(CleanupMemoryBeforeTestMixin, TestCase):

    def setUp(self):
        super(MemoryFSTests, self).setUp()
        self.temp_path = URI(tempfile.mktemp())
        self.temp_path.mkdir()
        self.root = URI("memory:///")


    def tearDown(self):
        if self.temp_path.isdir():
            self.temp_path.remove(recursive=True)
        super(MemoryFSTests, self).tearDown()


    def test_all(self):
        root = self.root
        assert root.isdir()

        subdir = root / "foo"

        subdir.mkdir()

        assert subdir.isdir()
        assert not subdir.isfile()

        out = subdir / "bar"

        with out.open("w") as outf:
            outf.write("foobar")

        assert not out.isdir()
        assert out.isfile()

        with out.open() as inf:
            content = inf.read()
            self.assertEqual(content, "foobar")


        assert subdir == root / "foo"

        time.sleep(.5)
        assert out.info().mtime < time.time()

        connection = subdir.connection
        out = StringIO()
        connection.dump(out)
        print((out.getvalue()))


    def test_write_text_read_binary(self):
        test_file = self.root / 'foo'
        with test_file.open('w') as text_proxy:
            text_proxy.write("spam & eggs")
        with test_file.open('rb') as binary_proxy:
            self.assertEqual(binary_proxy.read(), b"spam & eggs")


    def test_write_binary_read_text(self):
        test_file = self.root / 'foo'
        with test_file.open('wb') as binary_proxy:
            binary_proxy.write(b"spam & eggs")
        with test_file.open('r') as text_proxy:
            self.assertEqual(text_proxy.read(), "spam & eggs")


    def test_info_on_symlinks(self):
        root = self.root
        a_file = root / "a_file"
        a_link = root / "a_link"
        with a_file.open('w') as f:
            f.write("a" * 800)
        a_file.symlink(a_link)

        self.assertEqual(a_file.info().size, 800)
        self.assertEqual(a_link.info().size, 800)
        self.assertNotEqual(a_link.info(followlinks=False).size, 800)

        orig_info = a_file.info()
        new_info = a_file.info()
        new_info.mtime = new_info.mtime + 100
        a_link.info(new_info, followlinks=False)

        self.assertEqual(a_file.info().mtime, orig_info.mtime)
        self.assertEqual(a_link.info().mtime, orig_info.mtime)
        self.assertEqual(a_link.info(followlinks=False).mtime, new_info.mtime)


    def test_listdir_empty_root(self):
        root = self.root
        files = root.listdir()
        assert not files


    def test_listdir_empty_dir(self):
        root = self.root
        foo = root / 'foo'
        foo.mkdir()
        rootfiles = root.listdir()
        assert 'foo' in rootfiles
        foofiles = foo.listdir()
        assert not foofiles


    def test_walk(self):
        root = self.root
        foo = root / 'foo'
        foo.mkdir()
        bar = root / 'bar'
        bar.mkdir()
        foofile =  foo / 'foocontent.txt'
        with foofile.open('w') as fd:
            fd.write('foocontent')
        results = []
        for root, dirs, files in root.walk():
            results.append((root, dirs, files))
        assert len(results) == 3


    def test_next(self):
        root = self.root
        subdir = root / "foo"
        with subdir.open("w") as outf:
            outf.write("foo\nbar")

        with subdir.open() as inf:
            content = next(inf)
            self.assertEqual(content, "foo\n")
            content = next(inf)
            self.assertEqual(content, "bar")

        with subdir.open() as inf:
            for line in inf:
                self.assertIn(line, ["foo\n", "bar"])

    def test_exists_on_root(self):
        root = self.root
        assert root.exists()


    def test_root_of_non_existing_dir_exists(self):
        dir_path = URI("memory:///foo")
        assert dir_path.dirname().exists()


    def test_directory_cant_be_overwritten_by_file(self):
        base = URI("memory:///")
        d = base / "foo"
        d.mkdir()
        assert d.exists()

        try:
            with d.open("w") as outf:
                outf.write("foo")
        except IOError as e:
            self.assertEqual(e.errno, errno.EISDIR)
        else:
            assert False, "You shouldn't be able to ovewrite a directory like this"


    def test_copy_into_fs(self):
        root = self.root
        for item in ["foo", "bar"]:
            with (root/item).open("wb") as fd:
                fd.write(item.encode('utf-8'))
        root.copy(self.temp_path, recursive=True)
        content = self.temp_path.listdir()
        self.assertEqual(set(content), set(["foo", "bar"]))


    def test_cleanup_removes_lingering_locks(self):
        lockfile = self.root / "lockfile"
        with lockfile.open("w") as outf:
            outf.write(" ")

        lockfile._manipulate(mtime=lockfile.mtime() + 3, lock=True)
        CONNECTION_REGISTRY.cleanup(force=True)

        with lockfile.lock(fail_on_lock=True):
            pass


class TestRemovalOfFilesAndDirs(CleanupMemoryBeforeTestMixin, TestCase):

    def setUp(self):
        super(TestRemovalOfFilesAndDirs, self).setUp()
        self.root_path = URI('memory:///')

    def test_first(self):
        self.assertEqual(self.root_path.listdir(),[])

    def test_removedir(self):
        dir_path = self.root_path / 'foo'
        self.assertTrue(not dir_path.exists())
        dir_path.mkdir()
        self.assertTrue(dir_path.exists())
        self.assertTrue(dir_path.isdir())
        dir_path.remove()
        self.assertTrue(not dir_path.exists())

    def test_remove_not_existing_dir(self):
        dir_path = self.root_path / 'foo'
        self.assertRaises(FileDoesNotExistError, dir_path.remove, ())

    def test_removefile(self):
        file_path = self.root_path / 'foo.txt'
        self.assertTrue(not file_path.exists())
        with file_path.open('w') as fd:
            fd.write('bar')
        self.assertTrue(file_path.isfile())
        file_path.remove()
        self.assertTrue(not file_path.exists())


    def test_removefile_not_existing(self):
        file_path = self.root_path / 'foo.txt'
        self.assertRaises(FileDoesNotExistError, file_path.remove, ())


    def test_remove_recursive(self):
        dir_path = self.root_path / 'foo'
        file_path = dir_path / 'bar.txt'
        dir_path.mkdir()
        with file_path.open('w') as fd:
            fd.write('info')
        self.assertTrue(dir_path.exists())
        self.assertTrue(file_path.exists())
        dir_path.remove(recursive=True)
        self.assertTrue(not dir_path.exists())
        self.assertTrue(not file_path.exists())


    def test_locking(self):
        p = self.root_path / "test.txt"
        try:
            content = "I'm something written into a locked file"
            with p.lock() as inf:
                inf.write(content)
            self.assertEqual(p.open().read(), content)
        finally:
            if p.exists():
                p.remove()

        mfile = p.open("w")

        lock_a = mfile.lock
        mfile.close()

        mfile = p.open("w")
        assert lock_a is mfile.lock

        # artificially lock the file
        mfile.lock.acquire()

        try:
            with p.lock(fail_on_lock=True):
                assert False, "we shouldn't be allowed here!"
        except LockFileObtainException:
            pass
        finally:
            mfile.lock.release()


    def test_manipulation_api(self):
        p = self.root_path / "test.txt"
        p._manipulate(lock=True)
        mfile = p.open("w")
        assert not mfile.lock.acquire(False)
        p._manipulate(unlock=True)
        try:
            assert mfile.lock.acquire(False)
        finally:
            mfile.lock.release()

        with p.open("w") as outf:
            outf.write("foo")

        old_mtime = p.mtime()
        new_mtime = old_mtime + 100
        p._manipulate(mtime=new_mtime)

        self.assertEqual(p.mtime(), new_mtime)

        error_file = self.root_path / "error"

        with error_file.open("wb") as outf:
            outf.write(b"foobarbaz")

        error_dir = self.root_path / "error.dir"
        error_dir.mkdir()

        def next_op_callback(_path, _func):
            raise OSError(13, "Permission denied")

        for error in (error_file, error_dir):
            error._manipulate(next_op_callback=next_op_callback)
            clone = URI(error)
            try:
                clone.remove()
            except OSError as e:
                self.assertEqual(e.errno, 13)
            else:
                assert False, "Shouldn't be here"


    def test_reading_from_write_only_files_not_working(self):
        p = self.root_path / "test.txt"
        with p.open("w") as outf:
            self.assertRaises(IOError, outf.read)



    def test_lockfile_cleanup(self):
        p = self.root_path / "test.txt"
        if p.exists():
            p.remove()

        with p.lock(cleanup=True):
            assert p.exists()

        assert not p.exists()


    def test_file_name_comparison(self):
        a = self.root_path / "a"
        b = self.root_path / "b"
        assert a == a
        assert b == b
        assert a != b
        assert b != a
        assert not a != a
        assert not b != b


    def test_double_dir_creation_fails(self):
        a = self.root_path / "a"
        a.mkdir()
        self.assertRaises(OSError, a.mkdir)


    def test_setting_mode(self):
        p = self.root_path / "test.txt"
        if p.exists():
            p.remove()

        create_file(p, content="foo")

        mode = p.info().mode
        new_mode = mode | stat.S_IXUSR
        p.info(set_info=dict(mode=new_mode))
        self.assertEqual(p.info().mode,
                         new_mode)


    def test_removing_non_empty_dirs(self):
        p = self.root_path / "test-dir"
        assert not p.exists()
        p.mkdir()

        create_file(p / "some-file.txt", content="foobar")

        self.assertRaises(OSError, p.remove)

        (p / "some-file.txt").remove()
        p.remove()

        assert not p.exists()
        p.mkdir()

        create_file(p / "some-file.txt", content="foobar")

        p.remove(recursive=True)
