"""
This file contains unittests for chapter 1
"""

import lab1
import io
import sys
import unittest
from unittest import mock

class socket:
    URLs = {}
    Requests = {}

    def __init__(self, *args, **kwargs):
        self.request = b""
        self.connected = False

    def connect(self, host_port):
        self.scheme = "http"
        self.host, self.port = host_port
        self.connected = True

    def send(self, text):
        self.request += text
        self.method, self.path, _ = self.request.decode("latin1").split(" ", 2)

    def makefile(self, mode, encoding, newline):
        assert self.connected and self.host and self.port
        if self.port == 80 and self.scheme == "http":
            url = self.scheme + "://" + self.host + self.path
        elif self.port == 443 and self.scheme == "https":
            url = self.scheme + "://" + self.host + self.path
        else:
            url = self.scheme + "://" + self.host + ":" + str(self.port) + self.path
        self.Requests.setdefault(url, []).append(self.request)
        output = self.URLs[url]
        return io.StringIO(output.decode(encoding).replace(newline, "\n"), newline)

    def close(self):
        self.connected = False

    @classmethod
    def patch(cls):
        return mock.patch("socket.socket", wraps=cls)

    @classmethod
    def respond(cls, url, response):
        cls.URLs[url] = response

    @classmethod
    def last_request(cls, url):
        return cls.Requests[url][-1]

class ssl:
    def wrap_socket(self, s, server_hostname):
        assert s.host == server_hostname
        s.scheme = "https"
        return s

    @classmethod
    def patch(cls):
        return mock.patch("ssl.create_default_context", wraps=cls)

def errors(f, *args, **kwargs):
    try:
        f(*args, **kwargs)
    except Exception as e:
        return True
    else:
        return False
