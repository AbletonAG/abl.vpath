#******************************************************************************
# (C) 2008 Ableton AG
#******************************************************************************

import unittest

from abl.vpath.base.simpleuri import UriParse

class TestSimpleUri(unittest.TestCase):
    def test_one(self):
        uri = UriParse('file:///tmp/this')
        self.assertEqual(uri.path, '/tmp/this')

    def test_two(self):
        uri = UriParse('scheme:///some/path')
        self.assertEqual(uri.scheme, 'scheme')
        self.assertEqual(uri.path, '/some/path')

    def test_three(self):
        uri = UriParse('svn://user@host:/some/path')
        self.assertEqual(uri.scheme, 'svn')
        self.assertEqual(uri.path, '/some/path')
        self.assertEqual(uri.hostname, 'host')
        self.assertEqual(uri.username, 'user')

    def test_non_http_scheme(self):
        uri = UriParse('scheme://user:password@host:/some/path')
        self.assertEqual(uri.scheme, 'scheme')
        self.assertEqual(uri.path, '/some/path')
        self.assertEqual(uri.hostname, 'host')
        self.assertEqual(uri.username, 'user')
        self.assertEqual(uri.password, 'password')

    def test_non_http_uri_with_query_part(self):
        uri = UriParse('scheme:///some/path?key_one=val_one&key_two=val_two')
        self.assertEqual(uri.query,
                            {'key_one':'val_one', 'key_two':'val_two'}
                            )

    def test_query(self):
        uri = UriParse('http://heinz/?a=1')
        self.assertEqual(uri.query['a'], '1')
        uri = UriParse('http://heinz/?a=1&b=2')
        self.assertEqual(uri.query['a'], '1')
        self.assertEqual(uri.query['b'], '2')

    def test_query_unsplit(self):
        uri = UriParse('http://heinz/')
        uri.query = dict(a='1', b='2')
        self.assertEqual(uri, UriParse(str(uri)))

    def test_absolute_url(self):
        uri = UriParse('http:///local/path')
        self.assertEqual(str(uri), '/local/path')

    def test_relative_url(self):
        uri = UriParse('http://tmp/this')
        self.assertEqual(uri.scheme, 'http')
        self.assertEqual(uri.path, '/this')

    def test_relative_uri(self):
        uri = UriParse('file://./local/path')
        self.assertEqual(uri.path, './local/path')

    def test_suburi_as_serverpart(self):
        """
        functionality not yet implemented
        """
        uri = UriParse('scheme://((/path/to/local/file.zip))/content.txt')
        self.assertEqual(uri.hostname, '/path/to/local/file.zip')
        self.assertEqual(uri.path, '/content.txt')

if __name__ == '__main__':
    unittest.main()
