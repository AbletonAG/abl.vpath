from __future__ import with_statement

from cStringIO import StringIO
import errno
import os
import tempfile
import time
from unittest import TestCase

from abl.util import LockFileObtainException
from abl.vpath.base import URI
from abl.vpath.base.exceptions import FileDoesNotExistError
from abl.vpath.base.fs import CONNECTION_REGISTRY


class MemoryFSTests(TestCase):


    def setUp(self):
        CONNECTION_REGISTRY.cleanup(force=True)
        self.temp_path = URI(tempfile.mktemp())
        self.temp_path.mkdir()

    def tearDown(self):
        if self.temp_path.isdir():
            self.temp_path.remove(recursive=True)


    def test_all(self):
        root = URI("memory:///")
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
        print out.getvalue()


    def test_listdir_empty_root(self):
        root = URI("memory:///")
        files = root.listdir()
        assert not files


    def test_listdir_empty_dir(self):
        root = URI("memory:///")
        foo = root / 'foo'
        foo.mkdir()
        rootfiles = root.listdir()
        assert 'foo' in rootfiles
        foofiles = foo.listdir()
        assert not foofiles


    def test_walk(self):
        root = URI("memory:///")
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
        root = URI("memory:///")
        subdir = root / "foo"
        with subdir.open("w") as outf:
            outf.write("foo\nbar")

        with subdir.open() as inf:
            content = inf.next()
            assert content == "foo\n"
            content = inf.next()
            assert content == "bar"

        with subdir.open() as inf:
            for l in inf:
                assert l in ["foo\n", "bar"]

    def test_exists_on_root(self):
        root = URI("memory:///")
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
        except IOError, e:
            self.assertEqual(e.errno, errno.EISDIR)
        else:
            assert False, "You shouldn't be able to ovewrite a directory like this"


    def test_copy_into_fs(self):
        root = URI("memory:///")
        for item in ["foo", "bar"]:
            with (root/item).open("w") as fd:
                fd.write(item)
        root.copy(self.temp_path, recursive=True)
        content = self.temp_path.listdir()
        self.assertEqual(set(content), set(["foo", "bar"]))




class TestRemovalOfFilesAndDirs(TestCase):

    def setUp(self):
        CONNECTION_REGISTRY.cleanup(force=True)
        self.root_path = URI('memory:///')

    def test_first(self):
        self.assertEqual(self.root_path.listdir(),[])

    def test_removedir(self):
        dir_path = self.root_path / 'foo'
        self.assert_(not dir_path.exists())
        dir_path.mkdir()
        self.assert_(dir_path.exists())
        self.assert_(dir_path.isdir())
        dir_path.remove()
        self.assert_(not dir_path.exists())

    def test_remove_not_existing_dir(self):
        dir_path = self.root_path / 'foo'
        self.assertRaises(FileDoesNotExistError, dir_path.remove, ())

    def test_removefile(self):
        file_path = self.root_path / 'foo.txt'
        self.assert_(not file_path.exists())
        with file_path.open('w') as fd:
            fd.write('bar')
        self.assert_(file_path.isfile())
        file_path.remove()
        self.assert_(not file_path.exists())

    def test_removefile_not_existing(self):
        file_path = self.root_path / 'foo.txt'
        self.assertRaises(FileDoesNotExistError, file_path.remove, ())

    def test_remove_recursive(self):
        dir_path = self.root_path / 'foo'
        file_path = dir_path / 'bar.txt'
        dir_path.mkdir()
        with file_path.open('w') as fd:
            fd.write('info')
        self.assert_(dir_path.exists())
        self.assert_(file_path.exists())
        dir_path.remove(recursive=True)
        self.assert_(not dir_path.exists())
        self.assert_(not file_path.exists())


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



    def test_reading_from_write_only_files_not_working(self):
        p = self.root_path / "test.txt"
        with p.open("w") as outf:
            self.failUnlessRaises(IOError, outf.read)



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
        self.failUnlessRaises(IOError, a.mkdir)
