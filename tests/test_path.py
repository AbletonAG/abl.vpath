#******************************************************************************
# (C) 2008 Ableton AG
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
        self.assertEqual(
            URI('zip://((/path/to/file.zip))/content.txt'),
            testpath
            )

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

    def local_setup(self):
        self.writable = True
        self.walkable = True
        thisdir = os.path.split(os.path.abspath(__file__))[0]
        self.baseurl = 'file://' + thisdir
        self.foo_path = URI(self.baseurl) / 'foo'
        self.extras = {}

    def setUp(self):
        self.local_setup()
        self.existing_dir = ujoin(self.baseurl,'foo')
        self.existing_file = ujoin(self.baseurl, 'foo','foo.txt')
        self.non_existing_file = ujoin(self.baseurl, 'bar.txt')
        thisdir = os.path.split(os.path.abspath(__file__))[0]
        foo_dir = os.path.join(thisdir, 'foo')
        bar_dir = os.path.join(foo_dir, 'bar')
        os.mkdir(foo_dir)
        os.mkdir(bar_dir)
        some_file = os.path.join(foo_dir, 'foo.txt')
        with open(some_file, 'w') as fd:
            fd.write('content')

    def tearDown(self):
        thisdir = os.path.split(os.path.abspath(__file__))[0]
        foo_dir = os.path.join(thisdir, 'foo')
        shutil.rmtree(foo_dir)
        folder_dir = os.path.join(thisdir, 'folder')
        if os.path.isdir(folder_dir):
            shutil.rmtree(folder_dir)
        target_dir = os.path.join(thisdir, 'target')
        if os.path.isdir(target_dir):
            shutil.rmtree(target_dir)

    def test_file(self):
        if self.writable:
            path = URI(self.baseurl, **self.extras) / 'testfile.txt'
            with path.open('w') as fd:
                fd.write('hallo')
            with path.open() as fd:
                content = fd.read()
            self.assertEqual(content, 'hallo')
            self.assert_(path.exists())
            self.assert_(path.isfile())
            path.remove()
            self.assert_(not path.exists())
        path = URI(self.existing_file, **self.extras)
        self.assert_(path.exists())
        self.assert_(path.isfile())
        with path.open() as fd:
            content = fd.read()
        self.assert_(content)

    def test_dir(self):
        if self.writable:
            testdir = URI('testdir', **self.extras)
            testdir.makedirs()
            self.assert_(testdir.exists())
            self.assert_(testdir.isdir())
            self.assert_(not testdir.isfile())
            testfile = URI('testdir/somefile', **self.extras)
            with testfile.open('w') as fd:
                fd.write('test')
            testdir.remove(recursive=True)
            self.assert_(not testdir.exists())
            self.assert_(not testfile.exists())
        testdir = URI(self.existing_dir, **self.extras)
        self.assert_(testdir.exists())
        self.assert_(testdir.isdir())

    def test_listdir(self):
        path = URI(self.existing_dir, **self.extras)
        dirs = path.listdir()
        self.assert_('foo.txt' in dirs)

    def test_walk(self):
        if not self.walkable:
            return
        path = URI(self.existing_dir, **self.extras)
        for root, dirs, files in path.walk():
            if path == root:
                self.assert_('foo.txt' in files)
                self.assert_('bar' in dirs)

    def test_relative_walk(self):
        if not self.walkable:
            return
        path = URI(self.existing_dir, **self.extras)
        for root, relative, dirs, files in path.relative_walk():
            if path == root:
                self.assert_('foo.txt' in files)
                self.assert_('bar' in dirs)
                self.assertEqual(relative, '')
            if relative == 'bar':
                self.assert_(not dirs)
                self.assert_(not files)

    def test_copy_and_move_file(self):
        if not self.writable:
            return
        single_file = URI(self.non_existing_file, **self.extras)
        target_file = URI(self.baseurl, **self.extras) / 'target_file.txt'
        with single_file.open('w') as fs:
            fs.write('content')
        single_file.copy(target_file)
        self.assert_(target_file.exists())
        self.assert_(target_file.isfile())
        with target_file.open() as fs:
            self.assertEqual(fs.read(), 'content')
        target_file.remove()
        self.assert_(not target_file.exists())
        single_file.move(target_file)
        self.assert_(not single_file.exists())
        self.assert_(target_file.exists())
        self.assert_(target_file.isfile())
        with target_file.open() as fs:
            self.assertEqual(fs.read(), 'content')
        target_file.remove()

    def test_copy_and_move_dir(self):
        if not self.writable:
            return
        folder = URI(self.baseurl, **self.extras) / 'folder'
        folder.makedirs()
        self.assert_(folder.isdir())
        afile = folder / 'afile.txt'
        with afile.open('w') as fs:
            fs.write('content')
        target = URI(self.baseurl, **self.extras) / 'target'
        self.assert_(not target.exists())
        folder.copy(target, recursive=True)
        self.assert_(target.exists())
        target_file = target / 'afile.txt'
        self.assert_(target_file.exists())
        with target_file.open() as fs:
            content = fs.read()
            self.assertEqual(content, 'content')
        target.remove(recursive=True)
        self.assert_(not target.exists())
        target.makedirs()
        folder.copy(target, recursive=True)
        newtarget = target / 'folder'
        self.assert_(newtarget.exists())
        self.assert_(newtarget.isdir())
        newtarget_file = newtarget / 'afile.txt'
        self.assert_(newtarget_file.exists())
        self.assert_(newtarget_file.isfile())
        target.remove(recursive=True)

        folder.move(target)
        self.assert_(not folder.exists())
        self.assert_(target.exists())
        self.assert_(target.isdir())
        self.assert_(target_file.exists())
        self.assert_(target_file.isfile())
        target.remove(recursive=True)

    def test_move_folder_to_subfolder(self):
        """
        test moving a directory '/some/path/folder' to '/some/path/target'
        '/some/path/target' does already exist. It is expected that after
        the move '/some/path/target/folder' exists.
        """
        folder = self.foo_path / 'folder'
        content = folder / 'content_dir'
        and_more = content / 'and_more'
        and_more.makedirs()
        target = self.foo_path / 'target'
        target.makedirs()
        folder.move(target)
        self.assert_(not folder.exists())
        self.assert_(target.exists())
        self.assert_('folder' in target.listdir())
        self.assert_((target / 'folder').isdir())
        self.assert_((target / 'folder' / 'content_dir').isdir())

    def test_rename_folder(self):
        """
        test moving a directory '/some/path/folder' to '/some/path/target'
        '/some/path/target' does NOT yet exist. It is expected that after
        the move '/some/path/target' exists and is actually the former
        '/some/path/folder'.
        """
        folder = self.foo_path / 'folder'
        content = folder / 'content_dir'
        and_more = content / 'and_more'
        and_more.makedirs()
        target = self.foo_path / 'target'
        folder.move(target)
        self.assert_(not folder.exists())
        self.assert_(target.isdir())
        self.assert_('content_dir' in target.listdir())

    def test_backend(self):
        foo_path = self.foo_path
        bar_path = URI(self.foo_path.path+'?arg1=value1')
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
