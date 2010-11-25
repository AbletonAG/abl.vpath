#******************************************************************************
# (C) 2010 Ableton AG
#******************************************************************************

import unittest

from abl.vpath.base.uriparse import URIParser, urisplit

class TestURIParser(unittest.TestCase):

    def test_simple(self):
        result = ('scheme', '', '/some/path', None, None)
        self.assertEqual(urisplit('scheme:///some/path'), result)

    def test_with_authority_replace(self):
        result = ('scheme', 'file:///inner/path', '/some/path', None, None)
        self.assertEqual(urisplit('scheme://((file:///inner/path))/some/path'),
                         result)

    def test_special_file_notation(self):
        result = ('file', None, './relative/path', None, None)
        self.assertEqual(urisplit('file://./relative/path'), result)


if __name__ == '__main__':
    unittest.main()
