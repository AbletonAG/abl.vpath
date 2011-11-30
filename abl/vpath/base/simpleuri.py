#******************************************************************************
# (C) 2008 Ableton AG
#******************************************************************************
"""
simpleuri.py contains the UriParse class, which replaces pythons
urlparse module for non http urls
"""
from __future__ import with_statement, absolute_import

import re
from urlparse import urlparse
from urllib import urlencode, unquote_plus

from .uriparse import urisplit, split_authority


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
        self.authority = ''
        self.vpath_connector = ''
        self.fragment = ''
        if not '://' in uri:
            self.uri = 'file://'+uri
        (
            self.scheme,
            self.authority,
            self.path,
            self.query,
            self.fragment
            ) = urisplit(uri)
        if self.authority and '((' in self.authority:
            self.vpath_connector = self.authority[2:-2]
            self.authority = ''
        if self.authority:
            (
                self.username,
                self.password,
                self.hostname,
                self.port,
                ) = split_authority(self.authority)
            self.port = int(self.port or 0)
        if self.query:
            self.query = parse_query_string(self.query)
        else:
            self.query = {}

        if self.hostname:
            if self.port:
                self.netloc = ':'.join([self.hostname,str(self.port)])
            else:
                self.netloc = self.hostname

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
        if self.fragment:
            rest += '#%s' % self.fragment
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
        elif self.vpath_connector:
            parts.append("((%s))" % self.vpath_connector)
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
        netloc = ''
        if self.vpath_connector:
            netloc = '(('+self.vpath_connector+'))'
        else:
            netloc = self.netloc
        return [
            self.scheme,
            netloc,
            self.path,
            self.query,
            '',
            ]

def uri_from_parts(parts):
    "simple function to merge three parts into an uri"
    uri = "%s://%s%s" % (parts[0], parts[1], parts[2])
    if parts[3]:
        extra = '?'+urlencode(parts[3])
        uri += extra
    return uri
