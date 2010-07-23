from __future__ import with_statement

import time
from cStringIO import StringIO

from unittest import TestCase

from abl.vpath.base import URI
from abl.vpath.base.fs import CONNECTION_REGISTRY


class MemoryFSTests(TestCase):


    def setUp(self):
        CONNECTION_REGISTRY.connections = {}


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

