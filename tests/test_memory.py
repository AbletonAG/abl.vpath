from __future__ import with_statement

import time
from cStringIO import StringIO

from unittest import TestCase

from vpath.base import URI


class MemoryFSTests(TestCase):


    def test_all(self):
        root = URI("memory:///")
        assert root.isdir()

        subdir = root / "foo"

        subdir.mkdir()

        assert subdir.isdir()

        out = subdir / "bar"

        with out.open("w") as outf:
            outf.write("foobar")


        with out.open() as inf:
            content = inf.read()
            self.assertEqual(content, "foobar")


        assert subdir == root / "foo"

        time.sleep(.5)
        assert out.mtime() < time.time()

        connection = subdir.connection
        out = StringIO()
        connection.dump(out)
        print out.getvalue()



