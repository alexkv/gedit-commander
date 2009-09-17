import os
import types

class Struct(dict):
	def __getattr__(self, name):
		try:
			val = self[name]
		except KeyError:
			val = super(Struct, self).getattr(self, name)
		
		return val
	
	def __setattr__(self, name, value):
		if name in self:
			super(Struct, self).setattr(self, name, value)
		else:
			self[name] = value

def is_commander_module(mod):
	if type(mod) == types.ModuleType:
		return mod and ('__commander_module__' in mod.__dict__)
	else:
		mod = str(mod)
		return mod.endswith('.py') or (os.path.isdir(mod) and os.path.isfile(os.path.join(mod, '__init__.py')))
