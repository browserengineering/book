"""
This file contains unittests for chapter 1
"""

import lab1
import io
import socket
import sys
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
	def get_text(self, val):
		saved = sys.stdout
		output = io.StringIO();
		sys.stdout = output
		lab1.show(val)
		sys.stdout = saved
		return output.getvalue()

	def test_show(self):
		self.assertEqual('hello', self.get_text('<body>hello</body>'))
		self.assertEqual('hello', self.get_text('he<body>llo</body>'))
		self.assertEqual('hello', self.get_text('he<body>l</body>lo'))
		self.assertEqual('hello', self.get_text('he<body>l<div>l</div>o</body>'))

	@mock.patch('socket.socket', side_effect=mocked_socket)
	def test_request(self, mock_socket):
		(headers, body) = lab1.request('http://browser.engineering')
		self.assertEqual('Body text', body)
		self.assertEqual('Value1', headers['header1'])

if __name__ == '__main__':
	unittest.main()
