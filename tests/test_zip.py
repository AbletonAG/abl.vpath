from __future__ import with_statement
from unittest import TestCase

from abl.vpath.base import URI
from abl.vpath.base import zipfile26 as zipfile

from abl.vpath.base.zip import compare_parts, ISDIR, ISFILE, content_item
from abl.vpath.base.fs import CONNECTION_REGISTRY


def clean_registry():
    CONNECTION_REGISTRY.connections = {}


class ZipTestCase(TestCase):

    def setUp(self):
        clean_registry()

class TestHelper(TestCase):

    def test_content_item_in_root(self):
        path1 = '/'
        path2 = '/foo'
        self.assertEqual(content_item(path1, path2), 'foo')

    def test_dir_item_in_root(self):
        path1 = '/'
        path2 = '/foo/other'
        self.assertEqual(content_item(path1, path2), 'foo')

    def test_content_item_exists(self):
        path1 = '/foo'
        path2 = '/foo/bar'
        self.assertEqual(content_item(path1, path2), 'bar')

    def test_content_item_exists_not(self):
        path1 = '/foo'
        path2 = '/foofoo/bar'
        self.assertEqual(content_item(path1, path2), '')

    def test_compare_unequal(self):
        self.assert_(not compare_parts([1,2],[3,4]))

    def test_compare_ISDIR(self):
        self.assertEqual(compare_parts([1,2],[1,2,3]), ISDIR)

    def test_compare_ISFILE(self):
        self.assertEqual(compare_parts([1,2,3],[1,2,3]), ISFILE)

class TestWritingZip(ZipTestCase):

    def setUp(self):
        super(TestWritingZip, self).setUp()
        self.zip_uri = 'file://./file.zip'
        self.zip_path = URI(self.zip_uri)


    def tearDown(self):
        if self.zip_path.exists():
            self.zip_path.remove()


    def test_write_file_to_non_existing_zip(self):
        foo = URI('zip://((%s))/foo.txt' % self.zip_uri)
        with foo.open('w') as fd:
            fd.write('bar')


    def test_write_file_to_non_existing_zip_2(self):
        foo = URI('zip://((%s))/deeper/foo.txt' % self.zip_uri)
        with foo.open('w') as fd:
            fd.write('bar')


    def test_write_two_files(self):
        foo = URI('zip://((%s))/foo.txt' % self.zip_uri)
        with foo.open('w') as fd:
            fd.write('bar')
        bar = URI('zip://((%s))/bar.txt' % self.zip_uri)
        with bar.open('w') as fd:
            fd.write('foo')


class TestReadingZip(ZipTestCase):

    def setUp(self):
        super(TestReadingZip, self).setUp()
        self.zip_path = URI('memory:///file.zip')
        zip_handle = self.zip_path.open('wb')
        try:
            self.fp_zip = zipfile.ZipFile(zip_handle, 'w')
            self.fp_zip.writestr('/foo.txt', 'bar')
            self.fp_zip.close()
        finally:
            zip_handle.close()

    def tearDown(self):
        if self.zip_path.exists():
            self.zip_path.remove()


    def test_read_a_file(self):
        p = URI('zip://((memory:///file.zip))/foo.txt')
        with p.open() as fd:
            self.assertEqual(fd.read(), 'bar')

    def test_write_a_file(self):
        p = URI('zip://((memory:///file.zip))/bar.txt')
        with p.open('w') as fd:
            fd.write('foo')
        with p.open() as fd:
            self.assertEqual(fd.read(), 'foo')

    def test_exists(self):
        p = URI('zip://((memory:///file.zip))/foo.txt')
        with p.open('w') as fd:
            fd.write('foo')
        self.assert_(p.exists())

    def test_isfile(self):
        p = URI('zip://((memory:///file.zip))/foo.txt')
        with p.open('w') as fd:
            fd.write('foo')
        self.assert_(p.isfile())

    def test_isdir(self):
        dir_path = URI('zip://((memory:///file.zip))/somedir')
        p = dir_path / 'foo.txt'
        with p.open('w') as fd:
            fd.write('foo')
        self.assert_(dir_path.isdir())

    def test_path(self):
        dir_path = URI('zip://((memory:///file.zip))/somedir')
        self.assertEqual(dir_path.path, '/somedir')
        new_path = dir_path / 'other'
        self.assertEqual(new_path.path, '/somedir/other')

class TestListDir(ZipTestCase):
    def setUp(self):
        super(TestListDir, self).setUp()
        self.zip_path = URI('memory:///file.zip')

    def tearDown(self):
        if self.zip_path.exists():
            self.zip_path.remove()

    def test_listdir(self):
        base_path = URI('zip://((%s))/' % self.zip_path.uri)
        self.assertEqual(base_path.listdir(), [])
        p1 = URI('zip://((%s))/foo.txt' % self.zip_path.uri)
        with p1.open('w') as fd:
            fd.write('foo')
        self.assertEqual(base_path.listdir(), ['foo.txt'])
        p2 = URI('zip://((%s))/dir/foo.txt' % self.zip_path.uri)
        with p2.open('w') as fd:
            fd.write('foo')
        self.assertEqual(set(base_path.listdir()), set(['foo.txt', 'dir']))


class TestAdvancedZip(ZipTestCase):

    def setUp(self):
        super(TestAdvancedZip, self).setUp()
        self.zip_path = URI('memory:///file.zip')
        zip_handle = self.zip_path.open('wb')
        try:
            self.fp_zip = zipfile.ZipFile(zip_handle, 'w')
            self.fp_zip.writestr('/dir1/foo.txt', 'bar')
            self.fp_zip.writestr('/dir1/bar.txt', 'bar')
            self.fp_zip.writestr('/bar.txt', 'bar')
            self.fp_zip.close()
        finally:
            zip_handle.close()

    def tearDown(self):
        self.zip_path.remove()


    def test_walk(self):
        root = URI('zip://((%s))/' % self.zip_path.uri)
        self.assertEqual(len(root.listdir()), 2)
        rlist = []
        for base, dirs, files in root.walk():
            rlist.append((base, dirs, files))
        self.assertEqual(rlist,
                         [(root, ['dir1'], ['bar.txt']),
                          ((root / 'dir1'), [], ['bar.txt', 'foo.txt'])])


