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

class MockMainThreadRunner:
	def __init__(self, tab):
		self.tab = tab

	def schedule_animation_frame(self):
		self.tab.run_animation_frame()

	def schedule_script_task(self, script):
		script()

	def schedule_browser_task(self, callback):
		callback()

	def start(self):
		pass

	def run(self):
		pass
