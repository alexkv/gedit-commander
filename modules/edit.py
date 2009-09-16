"""Edit files or commands"""
import os
import gio
import gedit
import glob
import sys
import types
import inspect
import gio

import commander.commands as commands
import commands.completion
import commands.result

__commander_module__ = True

@commands.autocomplete(filename=commands.completion.filename)
def __default__(filename, view):
	"""Edit file: edit &lt;filename&gt;"""
	
	doc = view.get_buffer()
	cwd = os.getcwd()
	
	if not doc.is_untitled():
		cwd = os.path.dirname(doc.get_uri())
	else:
		cwd = os.path.expanduser('~/')
	
	if not os.path.isabs(filename):
		filename = os.path.join(cwd, filename)
	
	matches = glob.glob(filename)
	files = []
	
	if matches:
		for match in matches:
			files.append(gio.File(match).get_uri())
	else:
		files.append(gio.File(filename).get_uri())
	
	if files:
		window = view.get_toplevel()
		gedit.commands.load_uris(window, files)
		
	return commands.result.HIDE

locals()['file'] = __default__

def _mod_has_func(mod, func):
	return func in mod.__dict__ and type(mod.__dict__[func]) == types.FunctionType

def _mod_has_alias(mod, alias):
	return '__root__' in mod.__dict__ and alias in mod.__dict__['__root__']

def _edit_command(view, mod, func=None):
	try:
		uri = gio.File(inspect.getsourcefile(mod)).get_uri()
	except:
		return False

	if not func:
		gedit.commands.load_uri(view.get_toplevel(), uri)
	else:
		try:
			lines = inspect.getsourcelines(func)
			line = lines[-1]
		except:
			line = 0

		gedit.commands.load_uri(view.get_toplevel(), uri, None, line)
	
	return True

def _resume_command(view, mod, parts):
	if not parts:
		return _edit_command(view, mod)
	elif len(parts) == 1 and _mod_has_func(mod, parts[0]):
		return _edit_command(view, mod, mod.__dict__[parts[0]])
	elif len(parts) == 1 and _mod_has_alias(mod, parts[0]):
		return _edit_command(view, mod)
	
	if not parts[0]	in mod.__dict__:
		return False
	
	if not commands.is_commander_module(mod.__dict__[parts[0]]):
		return False
	
	return _resume_command(view, mod.__dict__[parts[0]], parts[1:])
		
def command(view, name):
	"""Edit commander command: edit.command &lt;command&gt;"""
	parts = name.split('.')
	
	for mod in sys.modules:
		if commands.is_commander_module(sys.modules[mod]) and (mod == parts[0] or _mod_has_alias(sys.modules[mod], parts[0])):
			if mod == parts[0]:
				ret = _resume_command(view, sys.modules[mod], parts[1:])
			else:
				ret = _resume_command(view, sys.modules[mod], parts)
			
			if not ret:
				raise commands.ExecuteException('Could not find command: ' + name)
			else:
				return commands.result.HIDE
	
	raise commands.ExecuteException('Could not find command: ' + name)

def new_command(view, name, **kwargs):
	"""Create a new commander command module: edit.new-command &lt;command&gt;"""
	
	filename = os.path.expanduser('~/.gnome2/gedit/commander/modules/' + name + '.py')
	
	if os.path.isfile(filename):
		raise commands.ExecuteException('Commander module ' + name + ' already exists')
	
	f = open(filename, 'w')
	f.write("import commands\n\n__commander_module__ = True\n\ndef __default__(view, *args, **kwargs):\n\t\"\"\"Some kind of cool new feature: cool &lt;something&gt;\n\nUse this to apply the cool new feature\"\"\"\n\tpass\n")
	f.close()
	
	kwargs['_cmd'] = filename
	return __default__(view, filename, **kwargs)
