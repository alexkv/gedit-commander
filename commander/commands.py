import os
import gio
import sys
import bisect
import types
import shlex
import inspect
import glib
from rollbackimporter import RollbackImporter
import re

def is_commander_module(mod):
	return mod and ('__commander_module__' in mod.__dict__) and ('__default__' in mod.__dict__)

class ExecuteException(Exception):
	def __init__(self, msg):
		self.msg = msg
	
	def __str__(self):
		return self.msg
	
class Commands:
	EXECUTE_DONE = 0
	EXECUTE_CONTINUE = 1
	EXECUTE_WAIT = 2
	
	class Method:
		def __init__(self, method, name, parent):
			self.method = method
			self.name = name.replace('_', '-')
			self.parent = parent
			self._func_props = None
		
		def commands(self):
			return []
		
		def cancel(self, view):
			if self.parent:
				self.parent.cancel(view, self)
		
		def cancel_continuation(self, view):
			if self.parent:
				self.parent.continuation(view, self)

		def doc(self):
			if self.method.__doc__:
				return self.method.__doc__.split("\n")[0]
			else:
				return 'Documentation not available'
		
		def parse_keywords(self, entry, args, splitted):
			newargs = []
			keywords = {'_cmd': args, '_entry': entry}
			
			for arg in splitted:
				if not isinstance(arg, basestring):
					newargs.append(arg)
					continue

				parts = arg.split('=', 1)
				
				if len(parts) == 2:
					keywords[parts[0]] = parts[1]
				else:
					newargs.append(arg)
			
			return newargs, keywords
		
		def execute(self, entry, view, args):
			if not self._func_props:
				self._func_props = inspect.getargspec(self.method)

			fp = self._func_props
			nargs = len(fp.args)
			
			splitted = shlex.split(args)
			
			if fp.args[0] == 'view':
				names = fp.args[1:]
				splitted.insert(0, view)
			else:
				names = fp.args
			
			defaults = []

			if fp.defaults:
				defaults = list(fp.defaults)
				
				if 'view' in defaults:
					defaults.remove('view')

			if fp.keywords:
				splitted, keywords = self.parse_keywords(entry, args, splitted)

			if len(splitted) < nargs - len(defaults):
				raise ExecuteException('Required arguments: ' + ', '.join(names))
			
			if len(splitted) > nargs and fp.varargs == None:
				raise ExecuteException('Required arguments: ' + ', '.join(names))

			if fp.keywords != None:
				# Parse the keywords
				return self.method(*splitted, **keywords)
			else:
				return self.method(*splitted)

		def __cmp__(self, other):
			if isinstance(other, Commands.Method):
				return cmp(self.name, other.name)
			else:
				return cmp(self.name, other)
		
	class Module(Method):
		def __init__(self, base, mod, parent=None):
			Commands.Method.__init__(self, None, base, parent)
			self._commands = None
			self._dirname = None

			if type(mod) == types.ModuleType:
				self.mod = mod
				self.method = mod.__dict__['__default__']
			else:
				self.mod = None
				self._dirname = mod
				self._rollback = RollbackImporter()
		
		def commands(self):
			if self._commands == None:
				self.scan_commands()

			return self._commands
		
		def cancel(self, view, cmd=None):
			if not self.mod:
				return False
			
			if '__cancel__' in self.mod.__dict__ and type(self.mod.__dict__['__cancel__']) == types.FunctionType:
				if not cmd:
					cmd = self.name
				else:
					cmd = cmd.name
					
				return self.mod.__dict__['__cancel__'](view, cmd)
			
			return False

		def cancel_continuation(self, view, cmd=None):
			if '__cancel_continuation__' in self.mod.__dict__ and type(self.mod.__dict__['__cancel_continuation__']) == types.FunctionType:
				if not cmd:
					cmd = self.name
				else:
					cmd = cmd.name

				self.mod.__dict__['__cancel_continuation__'](view, cmd)

		def clear(self):
			self._commands = None
		
		def alias(self):
			if not self.mod:
				return False

			return not self.mod.__name__.endswith(self.name.replace('-', '_'))
	
		def scan_commands(self):
			self._commands = []
			
			if self.mod == None:
				return

			dic = self.mod.__dict__

			for k in dic:
				if k.startswith('_'):
					continue
				
				item = dic[k]
				
				if type(item) == types.FunctionType:
					bisect.insort(self._commands, Commands.Method(item, k, self))
				elif type(item) == types.ModuleType and is_commander_module(item):
					mod = Commands.Module(k, item, self)
					bisect.insort(self._commands, mod)
					
					for mod in mod.expand_aliases():
						bisect.insort(self._commands, mod)
		
		def expand_aliases(self):
			mods = []
			
			for alias in self.aliases():
				mod = Commands.Module(alias, self.mod, self.parent)
				
				if (alias in self.mod.__dict__) and type(self.mod.__dict__[alias]) == types.FunctionType:
					mod.method = self.mod.__dict__[alias]
				
				mod._commands = []
				mods.append(mod)
			
			return mods
		
		def aliases(self):
			if not self.mod or self.alias():
				return []
			
			if '__aliases__' in self.mod.__dict__ and hasattr(self.mod.__dict__['__aliases__'], '__iter__'):
				return self.mod.__dict__['__aliases__']
			else:
				return []
		
		def do_reload(self):
			self._commands = None
			
			if not self._dirname:
				return
			
			oldpath = list(sys.path)
			
			try:
				self.mod = None
				
				self._rollback.uninstall()
				sys.path.insert(0, self._dirname)
				
				self._rollback.monitor()
				self.mod = __import__(self.name, globals(), locals(), [], 0)
				self._rollback.cancel()
				
				if not is_commander_module(self.mod):
					raise Exception('Module is not a commander module...')
				
				self.method = self.mod.__dict__['__default__']
			except:
				sys.path = oldpath
				self._rollback.uninstall()
				
				del sys.modules[self.name]
				raise
			
			sys.path = oldpath

	def __init__(self, dirs=[]):
		self._modules = None
		self._dirs = dirs
		self._monitors = []
		
		self._timeouts = {}
	
	def stop(self):
		for mon in self._monitors:
			mon.cancel()
		
		self._monitors = []
		self._modules = None
		
		for k in self._timeouts:
			glib.source_remove(self._timeouts[k])
		
		self._timeouts = {}
	
	def add_monitor(self, d):
		gfile = gio.File(d)
		monitor = gfile.monitor_directory(gio.FILE_MONITOR_NONE, None)
		
		if monitor:
			monitor.connect('changed', self.on_monitor_changed)
			self._monitors.append(monitor)
	
	def scan(self, d):
		files = []
		
		try:
			files = os.listdir(d)
		except OSError:
			pass
		
		for f in files:
			full = os.path.join(d, f)

			if f.endswith('.py') or os.path.isdir(full):
				if self.add_module(full) and os.path.isdir(full):
					self.add_monitor(full)
		
		self.add_monitor(d)
		
	def module_name(self, filename):
		return os.path.basename(os.path.splitext(filename)[0])
		
	def add_module(self, filename):
		base = self.module_name(filename)
		
		if base in self._modules:
			return
		
		try:
			mod = Commands.Module(base, os.path.dirname(filename))
		except Exception as e:
			print 'Could not add module', e
			return False

		bisect.insort_right(self._modules, mod)
		self.do_reload_module(mod)

		return True
		
	def ensure(self):
		if self._modules != None:
			return

		self._modules = []

		for d in self._dirs:
			self.scan(d)
	
	def expand_commands(self, commands):
		if commands == None:
			return self._modules

		newcmd = []

		for cmd in commands:
			for c in cmd.commands():
				if not isinstance(c, Commands.Module) or not c.alias():
					bisect.insort(newcmd, c)
				
		return newcmd

	def find(self, command, complete=False):
		parts = command.split('.')
		
		# Find the chain, do prefix completion
		if parts[0] == '':
			return None

		commands = None

		for i in parts:
			commands = self.expand_commands(commands)

			if len(commands) == 0:
				return None

			idx = bisect.bisect_left(commands, i)
			
			if idx >= len(commands):
				return None

			cmd = commands[idx]

			newcmd = []
			
			if not cmd.name.startswith(i):
				return None
			
			while cmd.name.startswith(i):
				newcmd.append(cmd)

				if not complete:
					break
				
				if idx == len(commands) - 1 or (not complete and len(newcmd) != 0):
					break
				
				idx = idx + 1
				cmd = commands[idx]

			commands = newcmd
		
		if not complete:
			return commands[0]
		else:
			return commands
	
	def complete(self, prefix):
		self.ensure()
		
		parts = prefix.split(' ', 1)
		cmds = None
		
		if len(parts) == 1:
			cmds = self.find(prefix, True)
		else:
			cmd = self.find(parts[0], False)
			
			if cmd:
				# Try to complete arguments
				parent = cmd.parent
				
				if not parent:
					parent = cmd
				
				if '__autocomplete__' in parent.__dict__:
					cmds = parent.__dict__['__autocomplete__'](parts[1])
		
		if cmds == None:
			return []
		else:
			return cmds			
	
	def execute(self, command, entry, view):
		if not command:
			return None, None

		self.ensure()
		
		parts = command.split(' ', 1)
		cmd = self.find(parts[0])
		
		if not cmd:
			m = re.match('^([^0-9a-zA-Z]+)(.*)', parts[0])
			
			if m:
				if m.group(2):
					if len(parts) > 1:
						parts[1] = m.group(2) + ' ' + parts[1]
					else:
						parts.append(m.group(2))

				cmd = self.find(m.group(1))
		
		if len(parts) == 1:
			args = ''
		else:
			args = parts[1]
		
		return cmd, args
	
	def on_timeout_delete(self):
		return False

	def do_reload_module(self, mod):
		# Find all aliases and remove them
		for alias in mod.aliases():
			idx = bisect.bisect_left(self._modules, alias)
			
			if self._modules[idx].name == alias:
				del self._modules[idx]
		
		# Now, try to reload the module
		try:
			mod.do_reload()
		except Exception as e:
			# Reload failed, we remove the module
			print 'Failed to reload module:', e
			self._modules.remove(mod)
			return

		# Reinstall aliases
		for m in mod.expand_aliases():
			bisect.insort(self._modules, m)

	def reload_module(self, path):
		if not self._modules or not path.endswith('.py'):
			return

		if path.endswith('__init__.py'):
			path = os.path.dirname(path)

		base = self.module_name(path)

		# Find module
		idx = bisect.bisect_left(self._modules, base)
		mod = None
		
		if idx < len(self._modules):
			mod = self._modules[idx]

		if not mod or mod.name != base:
			self.add_module(path)
			return
		
		self.do_reload_module(mod)
		
	def on_monitor_changed(self, monitor, gfile1, gfile2, evnt):
		if evnt == gio.FILE_MONITOR_EVENT_CHANGED:
			self.reload_module(gfile1.get_path())
		elif evnt == gio.FILE_MONITOR_EVENT_DELETED:
			path = gfile1.get_path()
			
			if path in self._timeouts:
				glib.source_remove(self._timeouts[path])
			
			self._timeouts[path] = glib.timeout_add(500, self.on_timeout_delete)
		elif evnt == gio.FILE_MONITOR_EVENT_CREATED:
			path = gfile1.get_path()
			
			if path in self._timeouts:
				glib.source_remove(self._timeouts[path])
				del self._timeouts[path]
			
			self.reload_module(path)
