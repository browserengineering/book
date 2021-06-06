"""
This file contains unittests for chapter 1
"""

import lab1
import socket
import unittest
from unittest import mock

def mocked_socket(*args, **kwargs):
	class MockReadline:
		def __init__(self, body):
			self.body = body
			self.count = 0

		def readline(self):
			if self.count == 0:
				self.count = self.count + 1
				return 'HTTP/1.0 200 OK'.format(self.body)
			elif self.count == 1:
				self.count = self.count + 1
				return 'Header1: Value1'				
			else:
				return "\r\n"

		def read(self):
			return self.body

	class MockSocket:
		def __init_(self):
			pass

		def connect(self, host_port):
			pass

		def send(self, text):
			pass

		def makefile(self, mode, encoding, newline):
			return MockReadline('Body text')

		def close(self):
			pass

	return MockSocket()

class TestLab1(unittest.TestCase):
  def test_show(self):
    self.assertEqual('hello', lab1.get_text('hello'))
    self.assertEqual('hello', lab1.get_text('<body>hello</body>'))
    self.assertEqual('hello', lab1.get_text('he<body>llo</body>'))
    self.assertEqual('hello', lab1.get_text('he<body>l</body>lo'))
    self.assertEqual('hello', lab1.get_text('he<body>l<div>l</div>o</body>'))

  @mock.patch('socket.socket', side_effect=mocked_socket)
  def test_request(self, mock_socket):
  	(headers, body) = lab1.request('http://browser.engineering')
  	self.assertEqual('Body text', body)
  	self.assertEqual('Value1', headers['header1'])

if __name__ == '__main__':
    unittest.main()
