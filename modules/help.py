from commands import Commands
import commands
import sys
import os
import types

__commander_module__ = True

def _help_command(entry, mod, func=None):
	doc = None
	
	if func:
		doc = func.__doc__
	elif mod.__doc__:
		doc = mod.__doc__
	elif '__default__' in mod.__dict__ and type(mod.__dict__['__default__']) == types.FunctionType:
		doc = mod.__dict__['__default__'].__doc__
	
	if not doc:
		doc = '<b>No documentation available</b>'
	else:
		parts = doc.split("\n")
		parts[0] = '<b>' + parts[0] + '</b>'
		doc = "\n".join(parts)

	entry.info_show(doc, True)
	return True
	
def _mod_has_func(mod, func):
	return func in mod.__dict__ and type(mod.__dict__[func]) == types.FunctionType

def _mod_has_alias(mod, alias):
	return '__aliases__' in mod.__dict__ and alias in mod.__dict__['__aliases__']

def _resume_command(entry, mod, parts):
	if not parts:
		return _help_command(entry, mod)
	elif len(parts) == 1 and _mod_has_func(mod, parts[0]):
		return _help_command(entry, mod, mod.__dict__[parts[0]])
	elif len(parts) == 1 and _mod_has_alias(mod, parts[0]):
		return _help_command(entry, mod)
	
	if not parts[0]	in mod.__dict__:
		return False
	
	if not commands.is_commander_module(mod.__dict__[parts[0]]):
		return False
	
	return _resume_command(entry, mod.__dict__[parts[0]], parts[1:])

def __default__(view, *args, **kwargs):
	parts = map(lambda x: x.replace('-', '_'), kwargs['_cmd'].split('.'))

	for mod in sys.modules:
		if commands.is_commander_module(sys.modules[mod]) and (mod == parts[0] or _mod_has_alias(sys.modules[mod], parts[0])):
			if mod == parts[0]:
				ret = _resume_command(kwargs['_entry'], sys.modules[mod], parts[1:])
			else:
				ret = _resume_command(kwargs['_entry'], sys.modules[mod], parts)
			
			if not ret:
				raise commands.ExecuteException('Could not find command: ' + kwargs['_cmd'])
			else:
				return True
