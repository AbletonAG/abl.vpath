#******************************************************************************
# (C) 2010 Ableton AG
#******************************************************************************

import unittest

from abl.vpath.base.uriparse import URIParser

class TestURIParser(unittest.TestCase):

    def test_simple(self):
        parser = URIParser()
        print parser.parse('scheme:///some/path')

if __name__ == '__main__':
    unittest.main()
