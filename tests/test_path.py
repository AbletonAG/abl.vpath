#******************************************************************************
# (C) 2008-2013 Ableton AG
#******************************************************************************
from __future__ import with_statement
import datetime
import os
import stat
from posixpath import join as ujoin
import shutil
import tempfile
from unittest import TestCase


from abl.vpath.base import *
from abl.vpath.base.fs import scheme_re


class KeepCurrentDir:
    def __init__(self, directory):
        self._directory = directory
        self._currentdir = os.getcwd()


    def __enter__(self):
        os.chdir(self._directory)
        return self


    def __exit__(self, *exc_args):
        os.chdir(self._currentdir)


class TestSchemeRe(TestCase):
    def test_file(self):
        m = scheme_re.match("file://something")
        self.assert_(m is not None)
        self.assertEqual(m.group(1), 'file')


    def test_with_plus(self):
        m = scheme_re.match("svn+ssh://something")
        self.assert_(m is not None)
        self.assertEqual(m.group(1), 'svn+ssh')


    def test_no_scheme(self):
        m = scheme_re.match("some/path")
        self.assertEqual(m, None)


class TestHttpUri(TestCase):
    def test_query(self):
        p = URI('http://storm/this')
        p.query['a'] = 'b'
        self.assertEqual(URI(str(p)), URI('http://storm/this?a=b'))


    def test_query_after_join(self):
        p = URI('http://storm/this')
        p /= 'other'
        self.assertEqual(URI(str(p)), URI('http://storm/this/other'))
        p.query['a'] = 'b'
        self.assertEqual(URI(str(p)), URI('http://storm/this/other?a=b'))


class TestUnicodeURI(TestCase):
    def setUp(self):
        self.thisdir = os.path.split(os.path.abspath(__file__))[0]
        self.foo_dir = os.path.join(self.thisdir, 'foo')
        self.bar_dir = os.path.join(self.thisdir, 'bar')


    def tearDown(self):
        p = URI(self.foo_dir)
        if p.isdir():
            p.remove(recursive=True)
        b = URI(self.bar_dir)
        if b.isdir():
            b.remove(recursive=True)


    def test_creation(self):
        local_path = URI(u'/tmp/this')
        self.assertEqual(local_path.path.split(os.sep), ['', 'tmp', 'this'])
        self.assertEqual(local_path.scheme, 'file')


    def test_mkdir(self):
        p = URI(unicode(self.foo_dir))
        p.mkdir()


    def test_unicode_extra(self):
        p = URI(self.foo_dir, some_query=u"what's up")


    def test_copy(self):
        p = URI(unicode(self.foo_dir))
        p.mkdir()
        dest = URI(self.bar_dir)
        p.copy(dest, recursive=True)


class TestCredentials(TestCase):
    """
    credentials (username, password) are treated as a special case
    """

    def test_regular(self):
        some_path = URI('scheme://username:password@host/some/path')
        self.assertEqual(some_path.username, 'username')
        self.assertEqual(some_path.password, 'password')


    def test_keyword_param(self):
        some_path = URI('scheme://host/some/path', username='username', password='password')
        self.assertEqual(some_path.username, 'username')
        self.assertEqual(some_path.password, 'password')


    def test_url_args(self):
        some_path = URI('scheme://host/some/path?username=username&password=password')
        self.assertEqual(some_path.username, 'username')
        self.assertEqual(some_path.password, 'password')


class TestURI(TestCase):
    def test_rescheming(self):
        some_path = URI('first:///scheme')
        some_path.scheme = 'second'
        joined_path = some_path / 'other'
        self.assertEqual(joined_path.scheme, 'second')


    def test_creation(self):
        local_path = URI('/tmp/this')
        self.assertEqual(local_path.path.split(os.sep), ['', 'tmp', 'this'])
        self.assertEqual(local_path.scheme, 'file')

        path = URI('localpath', sep='/')
        self.assertEqual(path.path, './localpath', path.path)

        path = URI('trailing/slash/', sep='/')
        self.assertEqual(path.path, './trailing/slash/')


    def test_split(self):
        local_path = URI('/some/long/dir/structure')
        pth, tail = local_path.split()
        self.assertEqual(pth, URI('/some/long/dir'))
        self.assertEqual(tail, 'structure')

        local_path = URI('somedir')
        pth, tail = local_path.split()
        self.assertEqual(pth, URI('.'))
        self.assertEqual(tail, 'somedir')


    def test_split_with_short_path(self):
        local_path = URI('/some')
        pth, tail = local_path.split()
        self.assertEqual(pth, URI('/'))
        self.assertEqual(tail, 'some')


    def test_split_with_args(self):
        local_path = URI('file:///some/long?extra=arg')
        pth, tail = local_path.split()
        self.assertEqual(tail, 'long')


    def test_root_split(self):
        pth = URI('/')
        directory, name = pth.split()
        self.assertEqual(directory, URI('/'))
        self.assertEqual(name, '')


    def test_win_somehow_broken_on_windows(self):
        path = URI("file://C:\\some\\windows\\path", sep='\\')
        self.assertEqual(path.path, r'C:\some\windows\path')
        self.assertEqual(path.uri, 'file:///C/some/windows/path')
        self.assertEqual(path.unipath, '/C/some/windows/path')


    def test_windows_repr(self):
        path = URI(r'C:\some\path\on\windows', sep='\\')
        self.assertEqual(path.path, r'C:\some\path\on\windows')
        self.assertEqual(path.uri, 'file:///C/some/path/on/windows')


    def test_split_windows(self):
        path = URI(r'C:\some\path\on\windows', sep='\\')
        pth, tail = path.split()
        self.assertEqual(pth.uri, 'file:///C/some/path/on')
        self.assertEqual(pth.path, r'C:\some\path\on')
        self.assertEqual(pth, URI(r'C:\some\path\on', sep='\\'))
        self.assertEqual(tail, 'windows')


    def test_join_windows(self):
        path = URI('C:\\some', sep='\\')
        self.assertEqual(path.uri, 'file:///C/some')
        new_path = path / 'other'
        self.assertEqual(new_path.uri, 'file:///C/some/other')


    def test_unipath_windows(self):
        path = URI('C:\\some?extra=arg', sep='\\')
        self.assertEqual(path.path, 'C:\\some')
        self.assertEqual(path.unipath, '/C/some')
        self.assertEqual(path.uri, 'file:///C/some?extra=arg')
        new_path = path / 'other'
        self.assertEqual(new_path.unipath, '/C/some/other')
        self.assertEqual(new_path.uri, 'file:///C/some/other?extra=arg')


    def test_relative_dir_and_unipath(self):
        path = URI('somedir', sep='\\')
        self.assertEqual(path.unipath, './somedir')


    def test_join(self):
        long_path = URI('this/is/a/long/path')
        self.assertEqual(long_path, URI('this') / 'is' / 'a' / 'long' / 'path')


    def test_augmented_join(self):
        testpath = URI('/a')
        testpath /= 'path'
        self.assertEqual(URI('/a/path'), testpath)


    def test_join_with_vpath_authority(self):
        testpath = URI('zip://((/path/to/file.zip))/')
        testpath /= 'content.txt'
        self.assertEqual(URI('zip://((/path/to/file.zip))/content.txt'),
                         testpath)


    def test_adding_suffix(self):
        testpath = URI("/a")
        other = testpath + ".foo"
        self.assertEqual(URI("/a.foo"), other)
        testpath += ".bar"
        self.assertEqual(URI("/a.bar"), testpath)


    def test_path_equality(self):
        pth_one = URI("/a")
        pth_two = URI("file:///a")
        self.assertEqual(pth_one, pth_two)


    def test_path_equals_path_with_trailing_slash(self):
        pth_one = URI("/a")
        pth_two = URI("/a/")
        self.assertNotEqual(pth_one, pth_two)
        self.assertEqual((pth_one / 'something'), (pth_two / 'something'))


    def test_extra_args(self):
        pth = URI("scheme://some/path?extra=arg")
        self.assertEqual(pth._extras(), {'extra':'arg'})


    def test_extra_args_and_kwargs(self):
        pth = URI("scheme://some/path?extra=arg", something='different')
        self.assertEqual(pth._extras(),
                        {'extra':'arg', 'something':'different'})


    def test_dirname(self):
        pth = URI("/this/is/a/path")
        self.assertEqual(pth.dirname(), URI("/this/is/a"))
        self.assertEqual(pth.dirname(level=2), URI("/this/is"))
        self.assertEqual(pth.dirname(level=3), URI("/this"))
        self.assertEqual(pth.dirname(level=4), URI("/"))
        self.assertEqual(pth.dirname(level=5), URI("/"))


class TestFileSystem(TestCase):
    def setUp(self):
        thisdir = os.path.split(os.path.abspath(__file__))[0]
        self.tmpdir = tempfile.mkdtemp('.temp', 'test-local-fs', thisdir)
        self.baseurl = 'file://' + self.tmpdir


    def tearDown(self):
        shutil.rmtree(self.tmpdir)


    def test_backend(self):
        foo_path = URI(self.baseurl) / 'foo'
        bar_path = URI(foo_path.path + '?arg1=value1')
        foo_2_path = foo_path / 'some_dir'
        self.assert_(foo_path.get_connection() is foo_2_path.get_connection())
        self.assert_(bar_path.get_connection() is not foo_path.get_connection())

        foo_path_connection = foo_path.get_connection()
        foo_path.query['arg'] = 'value'
        self.assert_(foo_path_connection is not foo_path.get_connection())


class TestEq(TestCase):
    def test_eq(self):
        """
        test for bugfix: __eq__ didn't check that 'other' is of URI type
        """
        p = URI('/some/path')
        self.assertNotEqual(p, None)
