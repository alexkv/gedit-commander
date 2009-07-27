from commands import Commands
import subprocess
import glib
import fcntl
import os
import tempfile
import signal
import commands
import gio

__commander_module__ = True
__aliases__ = ['!', '!!']
_running_process = None

class Process:
	def __init__(self, view, entry, pipe, replace, tmpin, stdout):
		self.pipe = pipe
		self.replace = replace
		self.tmpin = tmpin
		self.view = view
		self.entry = entry
		
		fcntl.fcntl(stdout, fcntl.F_SETFL, os.O_NONBLOCK)	
		conditions = glib.IO_IN | glib.IO_PRI | glib.IO_ERR | glib.IO_HUP
		
		if replace:
			self.view.set_editable(False)
		
		self.watch = glib.io_add_watch(stdout, conditions, self.collect_output)
		self._buffer = ''

	def update(self):
		parts = self._buffer.split("\n")
		
		for p in parts[:-1]:
			self.entry.info_show(p)
		
		self._buffer = parts[-1]

	def collect_output(self, fd, condition):
		if condition & (glib.IO_IN | glib.IO_PRI):
			try:
				self._buffer += fd.read()
				
				if not self.replace:
					self.update()
			except:
				self.entry.info_show(self._buffer.strip("\n"))
				self.stop()
				return False

		if condition & (glib.IO_ERR | glib.IO_HUP):
			if self.replace:
				buf = self.view.get_buffer()
				buf.begin_user_action()
				
				bounds = buf.get_selection_bounds()
				
				if not bounds:
					bounds = buf.get_bounds()
					
				buf.delete(bounds[0], bounds[1])
				buf.insert_at_cursor(self._buffer)
			else:
				self.entry.info_show(self._buffer.strip("\n"))
			
			self.stop()
			return False
		
		return True

	def stop(self):
		global _running_process

		self.pipe.kill()
		glib.source_remove(self.watch)
		
		if self.replace:
			self.view.set_editable(True)
		
		if self.tmpin:
			self.tmpin.close()
		
		_running_process = None
		self.entry.execute_done()

def _run_command(view, replace, **kwargs):
	global _running_process
	
	if _running_process:
		_running_process.stop()
		_running_process = None

	tmpin = None
	args = kwargs['_cmd']
	
	cwd = None
	doc = view.get_buffer()
	
	if not doc.is_untitled() and doc.is_local():
		gfile = gio.File(doc.get_uri())
		cwd = os.path.dirname(gfile.get_path())
	
	if '<!' in args:
		bounds = view.get_buffer().get_selection_bounds()
		
		if not bounds:
			bounds = view.get_buffer().get_bounds()

		inp = bounds[0].get_text(bounds[1])
		
		tmpin = tempfile.NamedTemporaryFile(delete=False)
		tmpin.write(inp)
		tmpin.flush()
		args = args.replace('<!', '< "' + tmpin.name + '"')

	try:
		p = subprocess.Popen(args, shell=True, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
		stdout = p.stdout

	except Exception, e:
		raise commands.ExecuteException('Failed to execute: ' + e)
	
	_running_process = Process(view, kwargs['_entry'], p, replace, tmpin, stdout)
	return Commands.EXECUTE_WAIT

def __default__(view, *args, **kwargs):
	"""Run shell command: ! &lt;command&gt;

You can use <b>&lt;!</b> as a special input meaning the current selection or current
document.
"""
	return _run_command(view, False, **kwargs)

def _run_replace(view, *args, **kwargs):
	"""Run shell command and place output in document: !! &lt;command&gt;

You can use <b>&lt;!</b> as a special input meaning the current selection or current
document.
"""
	return _run_command(view, True, **kwargs)

def __cancel__(view, command):
	global _running_process

	if _running_process:
		_running_process.stop()
		_running_process = None

		return True
	
	return False

locals()['!!'] = _run_replace

