import gedit
from windowhelper import WindowHelper
import commands
import os
import sys

class Commander(gedit.Plugin):
	def __init__(self):
		gedit.Plugin.__init__(self)
		self._instances = {}

		sys.path.insert(0, os.path.dirname(__file__))

		self.commands = commands.Commands([
			os.path.expanduser('~/.gnome2/gedit/commander/modules'),
			os.path.join(self.get_data_dir(), 'modules')
		])
        
	def activate(self, window):
		self._instances[window] = WindowHelper(self, window)

	def deactivate(self, window):
		self._instances[window].deactivate()
		del self._instances[window]
		
		if len(self._instances) == 0:
			self.commands.stop()

	def update_ui(self, window):
		self._instances[window].update_ui()
