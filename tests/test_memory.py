from __future__ import with_statement

import time
import errno
from cStringIO import StringIO

from unittest import TestCase

from abl.vpath.base import URI
from abl.vpath.base.exceptions import FileDoesNotExistError
from abl.vpath.base.fs import CONNECTION_REGISTRY


class MemoryFSTests(TestCase):


    def setUp(self):
        CONNECTION_REGISTRY.cleanup(force=True)


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
