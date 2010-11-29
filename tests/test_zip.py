from __future__ import with_statement
from unittest import TestCase

from abl.vpath.base import URI
from abl.vpath.base import zipfile26 as zipfile

from abl.vpath.base.zip import compare_parts, ISDIR, ISFILE, content_item

class TestHelper(TestCase):

    def test_content_item_in_root(self):
        path1 = '/'
        path2 = '/foo'
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

class TestReadingZip(TestCase):

    def setUp(self):
        self.zip_path = URI('memory:///file.zip')
        zip_handle = self.zip_path.open('wb')
        try:
            self.fp_zip = zipfile.ZipFile(zip_handle, 'w')
            self.fp_zip.writestr('/foo.txt', 'bar')
            self.fp_zip.close()
        finally:
            zip_handle.close()

    def tearDown(self):
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

class TestListDir(TestCase):
    def setUp(self):
        self.zip_path = URI('memory:///file.zip')

    def tearDown(self):
        if self.zip_path.exists():
            self.zip_path.remove()

    def test_listdir(self):
        base_path = URI('zip://((memory:///file.zip))/')
        self.assertEqual(base_path.listdir(), [])
        p1 = URI('zip://((memory:///file.zip))/foo.txt')
        with p1.open('w') as fd:
            fd.write('foo')
        self.assertEqual(base_path.listdir(), ['foo.txt'])

