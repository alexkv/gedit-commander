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
