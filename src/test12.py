from test11 import *
import lab12
import threading

class MockTimer:
	def __init__(self, sec, callback):
		self.sec = sec
		self.callback = callback

	def start(self):
		self.callback()

	def cancel(self):
		self.callback = None

threading.Timer = MockTimer

class MockMainThreadEventLoop:
	def __init__(self, tab):
		self.tab = tab

	def schedule_task(self, callback):
		callback()

	def clear_pending_tasks(self):
		pass

	def start(self):
		pass

	def run(self):
		pass

class MockNoOpMainThreadEventLoop:
	def __init__(self, tab):
		self.tab = tab

	def schedule_task(self, callback):
		pass

	def start(self):
		pass

	def run(self):
		pass