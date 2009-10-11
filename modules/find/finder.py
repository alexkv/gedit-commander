from xml.sax import saxutils
import commander.commands as commands

class Finder:
	FIND_STARTMARK = 'gedit-commander-find-startmark'
	FIND_ENDMARK = 'gedit-commander-find-endmark'
	
	def __init__(self, entry):
		self.entry = entry
		self.view = entry.view()
		
		self.findstr = None
		self.replacestr = None

		self.marks = [None, None]
		
		self.unescapes = [
			['\\n', '\n'],
			['\\r', '\r'],
			['\\t', '\t']
		]
		
		self.from_start = False
		self.last_insert_mark = None
	
	def unescape(self, s):
		for esc in self.unescapes:
			s = s.replace(esc[0], esc[1])
		
		return s
	
	def do_find(self, bounds):
		return None
	
	def get_replace(self, text):
		return self.replacestr
	
	def set_replace(self, replacestr):
		self.replacestr = self.unescape(replacestr)
	
	def set_find(self, findstr):
		self.findstr = self.unescape(findstr)
	
	def find_next(self):
		buf = self.view.get_buffer()
		
		bounds = [buf.get_iter_at_mark(buf.get_selection_bound()),
			      buf.get_iter_at_mark(self.marks[1])]

		ret = self.do_find(bounds)
	
		if not ret and not self.marks[0] and not self.from_start:
			self.from_start = True

			# Try from beginning
			bounds[0] = buf.get_start_iter()
			bounds[1] = buf.get_iter_at_mark(self.last_insert_mark)
			
			self.marks[1] = self.last_insert_mark
			
			ret = self.do_find(bounds)
	
		if not ret:
			return False
		else:
			# Goto
			buf.move_mark(buf.get_insert(), ret[0])
			buf.move_mark(buf.get_selection_bound(), ret[1])

			visible = self.view.get_visible_rect()
			loc = self.view.get_iter_location(ret[0])

			# Scroll there if needed
			if loc.y + loc.height < visible.y or loc.y > visible.y + visible.height:
				self.view.scroll_to_mark(buf.get_insert(), 0.2, True, 0, 0.5)

			return True

	def find_first(self, doend=True):
		words = []
		buf = self.view.get_buffer()
	
		while not self.findstr:
			fstr, words, modifier = (yield commands.result.Prompt('Find:'))
			
			if fstr:
				self.set_find(fstr)
		
		# Determine search area
		bounds = list(buf.get_selection_bounds())
		
		if self.last_insert_mark:
			buf.delete_mark(self.last_insert_mark)
			self.last_insert_mark = None
		
		if not bounds:
			bounds = list(buf.get_bounds())
			self.marks[0] = None
			self.last_insert_mark = buf.create_mark(None, buf.get_iter_at_mark(buf.get_insert()), True)
		else:
			bounds[0].order(bounds[1])
			
			self.marks[0] = buf.get_mark(Finder.FIND_STARTMARK)
		
			if not self.marks[0]:
				self.marks[0] = buf.create_mark(Finder.FIND_STARTMARK, bounds[0], True)
			else:
				buf.move_mark(self.marks[0], bounds[0])
		
		self.marks[1] = buf.get_mark(Finder.FIND_ENDMARK)
	
		if not self.marks[1]:
			self.marks[1] = buf.create_mark(Finder.FIND_ENDMARK, bounds[1], False)
		else:
			buf.move_mark(self.marks[1], bounds[1])

		if self.marks[0]:
			start = buf.get_iter_at_mark(self.marks[0])

			buf.move_mark(buf.get_selection_bound(), start)
			buf.move_mark(buf.get_insert(), start)
		else:
			buf.move_mark(buf.get_selection_bound(), buf.get_iter_at_mark(buf.get_insert()))

		if not self.find_next():
			if doend:
				self.entry.info_show('<i>Search hit end of the document</i>', True)

			yield commands.result.DONE
		else:
			yield True
	
	def cancel(self):
		buf = self.view.get_buffer()

		buf.set_search_text('', 0)
		buf.move_mark(buf.get_selection_bound(), buf.get_iter_at_mark(buf.get_insert()))
		
		if self.last_insert_mark:
			buf.delete_mark(self.last_insert_mark)
	
	def find(self, findstr):
		if findstr:
			self.set_find(findstr)

		buf = self.view.get_buffer()

		try:
			if (yield self.find_first()):
				while True:
					argstr, words, modifier = (yield commands.result.Prompt('Search next [<i>%s</i>]:' % (saxutils.escape(self.findstr),)))
	
					if argstr:
						self.set_find(argstr)

					if not self.find_next():
						break

				self.entry.info_show('<i>Search hit end of the document</i>', True)
		except GeneratorExit as e:
			self.cancel()
			raise e

		self.cancel()
		yield commands.result.DONE
	
	def _restore_cursor(self, mark):
		buf = mark.get_buffer()

		buf.move_mark(buf.get_insert(), buf.get_iter_at_mark(mark))
		buf.move_mark(buf.get_selection_bound(), buf.get_iter_at_mark(mark))
		buf.delete_mark(mark)
		
		self.view.scroll_to_mark(buf.get_insert(), 0.2, True, 0, 0.5)
	
	def replace(self, findstr, replaceall=False, replacestr=None):
		if findstr:
			self.set_find(findstr)

		if replacestr != None:
			self.set_replace(replacestr)

		# First find something
		buf = self.view.get_buffer()
		
		if replaceall:
			startmark = buf.create_mark(None, buf.get_iter_at_mark(buf.get_insert()), False)
		
		ret = (yield self.find_first())
		
		if not ret:
			yield commands.result.DONE
	
		# Then ask for the replacement string
		if not self.replacestr:
			try:
				replacestr, words, modifier = (yield commands.result.Prompt('Replace with:'))
				self.set_replace(replacestr)
			except GeneratorExit as e:
				if replaceall:
					self._restore_cursor(startmark)

				self.cancel()
				raise e

		# On replace all, wrap it in begin/end user action
		if replaceall:
			buf.begin_user_action()

		try:
			while True:
				if not replaceall:
					rep, words, modifier = (yield commands.result.Prompt('Replace next [%s]:' % (saxutils.escape(self.replacestr),)))
			
					if rep:
						self.set_replace(rep)

				bounds = buf.get_selection_bounds()

				# If there is a selection, replace it with the replacement string
				if bounds:
					text = bounds[0].get_text(bounds[1])
					repl = self.get_replace(text)

					buf.begin_user_action()
					buf.delete(bounds[0], bounds[1])
					buf.insert(bounds[1], repl)
	
					buf.move_mark(buf.get_insert(), bounds[1])
					buf.end_user_action()

				# Find next
				if not self.find_next():
					if not replaceall:
						self.entry.info_show('<i>Search hit end of the document</i>', True)

					break
	
		except GeneratorExit as e:
			if replaceall:
				self._restore_cursor(startmark)
				buf.end_user_action()

			self.cancel()
			raise e				

		if replaceall:
			self._restore_cursor(startmark)

			buf.end_user_action()

		self.cancel()
		yield commands.result.DONE
