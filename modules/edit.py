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
import commander.commands.completion
import commander.commands.result
import commander.commands.exceptions

__commander_module__ = True

@commands.autocomplete(filename=commander.commands.completion.filename)
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
		
	return commander.commands.result.HIDE

def _dummy_cb(num, total):
	pass

def rename(view, newfile):
	"""Rename current file: edit.rename &lt;newname&gt;"""
	
	doc = view.get_buffer()
	
	if not hasattr(doc, 'set_uri'):
		raise commander.commands.exceptions.Execute('Your version of gedit does not support this action')
	
	if doc.is_untitled():
		raise commander.commands.exceptions.Execute('Document is unsaved and thus cannot be renamed')
	
	if doc.get_modified():
		raise commander.commands.exceptions.Execute('You have unsaved changes in your document')
	
	if not doc.is_local():
		raise commander.commands.exceptions.Execute('You can only rename local files')
	
	f = gio.File(doc.get_uri())
	
	if not f.query_exists():
		raise commander.commands.exceptions.Execute('Current document file does not exist')
	
	if os.path.isabs(newfile):
		dest = gio.File(newfile)
	else:
		dest = f.get_parent().resolve_relative_path(newfile)
	
	if f.equal(dest):
		yield commander.commands.result.HIDE
	
	if not dest.get_parent().query_exists():
		# Check to create parent directory
		fstr, words, modifierret = (yield commands.result.Prompt('Directory does not exist, create? [Y/n] '))
		
		if fstr.strip().lower() in ['y', 'ye', 'yes', '']:
			# Create parent directories
			try:
				os.makedirs(dest.get_parent().get_path())
			except OSError, e:
				raise commander.commands.exceptions.Execute('Could not create directory')
		else:
			yield commander.commands.result.HIDE
	
	if dest.query_exists():
		fstr, words, modifierret = (yield commands.result.Prompt('Destination already exists, overwrite? [Y/n]'))
		
		if not fstr.strip().lower() in ['y', 'ye', 'yes', '']:
			yield commander.commands.result.HIDE
	
	try:
		f.move(dest, _dummy_cb, flags=gio.FILE_COPY_OVERWRITE)
		
		doc.set_uri(dest.get_uri())
		yield commander.commands.result.HIDE
	except Exception, e:
		raise commander.commands.exceptions.Execute('Could not move file: %s' % (e,))

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
	
	func = parts[0].replace('-', '_')

	if len(parts) == 1 and _mod_has_func(mod, func):
		return _edit_command(view, mod, mod.__dict__[func])
	elif len(parts) == 1 and _mod_has_alias(mod, parts[0]):
		return _edit_command(view, mod)
	
	if not func in mod.__dict__:
		return False
	
	if not commands.is_commander_module(mod.__dict__[func]):
		return False
	
	return _resume_command(view, mod.__dict__[func], parts[1:])

@commands.autocomplete(name=commander.commands.completion.command)
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
				raise commander.commands.exceptions.Execute('Could not find command: ' + name)
			else:
				return commander.commands.result.HIDE
	
	raise commander.commands.exceptions.Execute('Could not find command: ' + name)

def new_command(view, entry, name):
	"""Create a new commander command module: edit.new-command &lt;command&gt;"""
	
	filename = os.path.expanduser('~/.gnome2/gedit/commander/modules/' + name + '.py')
	
	if os.path.isfile(filename):
		raise commander.commands.exceptions.Execute('Commander module `' + name + '\' already exists')
	
	f = open(filename, 'w')
	f.write("import commander.commands\n\n__commander_module__ = True\n\ndef __default__(view, entry):\n\t\"\"\"Some kind of cool new feature: cool &lt;something&gt;\n\nUse this to apply the cool new feature\"\"\"\n\tpass\n")
	f.close()
	
	return __default__(filename, view)

locals()['file'] = __default__
move = rename
