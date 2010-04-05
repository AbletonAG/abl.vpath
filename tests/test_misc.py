#******************************************************************************
# (C) 2009 Ableton AG
# author: Stephan Diehl (std)
# email: stephan.diehl@ableton.com
#******************************************************************************
from __future__ import with_statement
import os

from vpath.base.misc import Bunch, TempFileHandle


class TestBunch:
    def test_creation(self):
        bunch = Bunch(a=1)
        assert hasattr(bunch, 'a')
        assert 'a' in bunch
        assert bunch.a == 1

    def test_deletion(self):
        bunch = Bunch(a=1)
        del bunch.a
        assert not hasattr(bunch, 'a')
        assert 'a' not in bunch

    def test_copy(self):
        bunch = Bunch(a=1)
        the_copy = bunch.copy()
        assert bunch is not the_copy
        assert bunch == the_copy

    def test_subclassing_and_copy(self):
        class MyBunch(Bunch):pass
        my_bunch = MyBunch(a=1)
        my_bunch_copy = my_bunch.copy()
        assert isinstance(my_bunch_copy, MyBunch), type(my_bunch_copy)


    def test_get_prefix(self):
        bunch = Bunch(
            a_a=1,
            a_b=2,
            b_a=3
            )
        assert bunch.get_prefix('a') == {'a_a':1, 'a_b':2}

class TestTempFileHandle:
    def test_handle(self):
        fs = open('testfile', 'w')
        fs.write('hallo')
        fs.close()
        with TempFileHandle('testfile') as fs:
            content = fs.read()
        assert content == 'hallo'
        assert not os.path.exists('testfile')

