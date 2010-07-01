#******************************************************************************
# (C) 2008 Ableton AG
#******************************************************************************

from abl.vpath.base.simpleuri import UriParse

def test_non_http_uri_with_query_part():
    uri = UriParse('scheme:///some/path?key_one=val_one&key_two=val_two')
    assert uri.query == {'key_one':'val_one', 'key_two':'val_two'}

def test_one():
    uri = UriParse('file:///tmp/this')
    assert uri.path == '/tmp/this'

def test_two():
    uri = UriParse('scheme:///some/path')
    assert uri.scheme == 'scheme'
    assert uri.path == '/some/path'

def test_three():
    uri = UriParse('svn://user@host:/some/path')
    assert uri.scheme == 'svn'
    assert uri.path == '/some/path'
    assert uri.hostname == 'host'
    assert uri.username == 'user'

def test_four():
    uri = UriParse('svn://user:passwd@host:/some/path')
    assert uri.scheme == 'svn'
    assert uri.path == '/some/path'
    assert uri.hostname == 'host'
    assert uri.username == 'user'
    assert uri.password == 'passwd'

def test_five():
    uri = UriParse('file://tmp/this')
    assert uri.scheme == 'file'
    assert uri.path == 'tmp/this'

def test_six():
    uri = UriParse('svn://versonator:+UPa&U)n_r+:3fk@heinz/Build/trunk/IntegrationTools')
    assert uri.username == 'versonator'
    assert uri.password == '+UPa&U)n_r+:3fk'

def test_query():
    uri = UriParse('http://heinz/?a=1')
    assert uri.query['a'] == '1'
    uri = UriParse('http://heinz/?a=1&b=2')
    assert uri.query['a'] == '1'
    assert uri.query['b'] == '2'

def test_query_unsplit():
    uri = UriParse('http://heinz/')
    uri.query = dict(a='1', b='2')
    assert uri == UriParse(str(uri))

def test_absolute_url():
    uri = UriParse('http:///local/path')
    assert str(uri) == '/local/path'

def test_relative_url():
    uri = UriParse('http://./local/path')
    assert str(uri) == 'local/path'

def xtest_suburi_as_serverpart():
    """
    functionality not yet implemented
    """
    uri = UriParse('zip://((/path/to/local/file.zip))/content.txt')
    assert uri.hostname == '/path/to/local/file.zip'
    assert uri.path == '/content.txt'

