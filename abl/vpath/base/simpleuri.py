"""
simpleuri.py contains the UriParse class, which replaces pythons
urlparse module for non http urls
"""
#******************************************************************************
# (C) 2008 Ableton AG
#******************************************************************************

from urlparse import urlparse
from urllib import urlencode, unquote_plus

def parse_query_string(query):
    """
    parse_query_string:
    very simplistic. won't do the right thing with list values
    """
    result = {}
    qparts = query.split('&')
    for item in qparts:
        key, value = item.split('=')
        key = key.strip()
        value = value.strip()
        result[key] = unquote_plus(value)
    return result

class UriParse(object):
    """
    UriParse is a simplistic replacement for urlparse, in case the uri
    in question is not a http url.
    """
    def __init__(self, uri=''):
        """
        starts to get complicated: ouchh...

        we want to have support for http urls in the following way:

        1. after url creation, the query key, value pairs need to be set
           and need to show up when using the 'str' function on the url:

           >>> url = UriParse('http://host/some/path')
           >>> url.query['key1] = 'value1'
           >>> str(url) == 'http://host/some/path?key1=value1'
           True

        2. absolute urls like 'http:///some/absolute/path' should work:

           >>> url = UriParse('http:///absolute/path')
           >>> str(url) == '/absolute/path'
           True

        3. relative urls like 'http://./some/relative/path should work:

            >>> url = UriParse('http://./relative/path')
            >>> str(url) == 'relative/path'
            True
        """
        self.uri = uri
        self.hostname = self.username = self.password = ''
        self.netloc = ''
        self.port = 0
        self.query = {}
        self.scheme = ''
        self.path = ''
        if uri.startswith('http://') or uri.startswith('https://'):
            self._init_as_http_url()
        else:
            self._init_other_uri()


    def _init_as_http_url(self):
        """
        init code when having a http url
        """
        parsed = urlparse(self.uri)
        self.hostname = parsed.hostname
        self.username = parsed.username
        self.password = parsed.password
        self.netloc = parsed.netloc
        self.port = parsed.port
        if self.hostname != '.':
            self.path = parsed.path
        else:
            self.hostname = ''
            self.path = parsed.path[1:]
        self.scheme = parsed.scheme
        if not self.port:
            self.port = 0
        if parsed.query:
            self.query = parse_query_string(parsed.query)

    def _init_other_uri(self):
        "init code for non http uri"
        uri, querysep, rest = self.uri.partition('?')
        if querysep:
            self.uri = uri
            self.query = parse_query_string(rest)
        parts = self.uri.split('://', 1)
        if len(parts) == 2:
            self.scheme, rest = parts
        else:
            self.scheme = 'file'
            self.path = self.uri
            return
        if self.scheme == 'file':
            self.path = rest
            return
        head = ''
        if rest.startswith('.') or rest.startswith('/'):
            self.path = rest
        else:
            parts = rest.split('/', 1)
            if len(parts) == 2:
                head, path = parts
                self.path = '/'+path
                self.netloc = head
            else:
                self.path = parts[0]
        parts = head.split('@', 1)
        if len(parts) == 2:
            host = parts[1]
            hparts = host.split(':', 1)
            if len(hparts) == 2:
                port = hparts[1]
                if port:
                    self.port = int(port)
            self.hostname = hparts[0]
            uparts = parts[0].split(':', 1)
            if len(uparts) == 2:
                self.password = uparts[1]
            self.username = uparts[0]
        else:
            self.hostname = self.netloc = parts[0]


    def __repr__(self):
        return '<SimpleUri (%s,%s,%s,%s,%s,%s) %s>' % (
            self.scheme,
            self.hostname,
            self.port,
            self.username,
            self.password,
            self.query,
            self.path
            )

    def __str__(self):
        if self.query:
            qup = ['%s=%s' % (key, value) for key, value in self.query.items()]
            rest = '?'+('&'.join(qup))
        else:
            rest = ''
        if (
            (self.scheme.startswith('http') and self.hostname) or 
            not self.scheme.startswith('http')
            ):
            parts = [self.scheme, '://']
        else:
            parts = []
        if self.username:
            parts.append(self.username)
        if self.password:
            parts += [':', self.password]
        if self.username or self.password:
            parts.append('@')
        if self.hostname:
            parts.append(self.hostname)
        if self.port:
            parts += [':', str(self.port)]
        parts += [self.path, rest]

        return ''.join(parts)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False

        return (
            self.scheme == other.scheme and
            self.netloc == other.netloc and
            self.path == other.path and
            self.query == other.query
            )

    def as_list(self):
        "return some attributes as a list"
        return [self.scheme, self.netloc, self.path, self.query, '']

def uri_from_parts(parts):
    "simple function to merge three parts into an uri"
    uri = "%s://%s%s" % (parts[0], parts[1], parts[2])
    if parts[3]:
        extra = '?'+urlencode(parts[3])
        uri += extra
    return uri
