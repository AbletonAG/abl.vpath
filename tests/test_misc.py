#******************************************************************************
# (C) 2009 Ableton AG
# author: Stephan Diehl (std)
# email: stephan.diehl@ableton.com
#******************************************************************************
from __future__ import with_statement
import os
from unittest import TestCase

from abl.vpath.base.misc import TempFileHandle
from abl.vpath.base import URI

from .common import CleanupMemoryBeforeTestMixin


class TestTempFileHandle(object):
    def test_handle(self):
        fs = open('testfile', 'w')
        fs.write('hallo')
        fs.close()
        with TempFileHandle('testfile') as fs:
            content = fs.read()
        assert content == 'hallo'
        assert not os.path.exists('testfile')


class TestGlob(CleanupMemoryBeforeTestMixin, TestCase):

    def test_globbing_by_prefix(self):
        base = URI("memory:///")
        a = base / "a.foo"
        b = base / "b.bar"

        for f in [a, b]:
            with f.open("w") as outf:
                outf.write("foo")

        self.assertEqual([a], base.glob("*.foo"))


    def test_globbing_by_prefix_in_subdir(self):
        base = URI("memory:///") / "dir"
        base.mkdir()
        a = base / "a.foo"
        b = base / "b.bar"

        for f in [a, b]:
            with f.open("w") as outf:
                outf.write("foo")

        self.assertEqual([a], base.glob("*.foo"))


    def test_globbing_by_suffix(self):
        base = URI("memory:///")
        a = base / "a.foo"
        b = base / "b.bar"

        for f in [a, b]:
            with f.open("w") as outf:
                outf.write("foo")

        self.assertEqual([a], base.glob("a.*"))


    def test_globbing_by_suffix_in_subdir(self):
        base = URI("memory:///") / "dir"
        base.mkdir()
        a = base / "a.foo"
        b = base / "b.bar"

        for f in [a, b]:
            with f.open("w") as outf:
                outf.write("foo")

        self.assertEqual([a], base.glob("a.*"))
