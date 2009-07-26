from commands import Commands
import gedit
import re

__commander_module__ = True

class FindState:
	def __init__(self, reg, flags, find, bound):
		self.find = find
		self.flags = flags
		self.bound = bound
		self.regex = reg
		self.replace = None

_find_state = None

def _find(view, flags, **kwargs):
	global _find_state
	
	buf = view.get_buffer()
	flags = re.UNICODE | re.MULTILINE | re.DOTALL | flags
	
	view.get_buffer().set_search_text('', gedit.SEARCH_DONT_SET_FLAGS)
	
	cmd = kwargs['_cmd']
	entry = kwargs['_entry']
	
	if not _find_state and not cmd:
		# Ask for a search text first
		entry.prompt('Find:')
		entry.enable_continuation()

		return False
	
	if _find_state and (not cmd or (cmd == _find_state.find and flags == _find_state.flags)):
		bounds = (buf.get_iter_at_mark(buf.get_selection_bound()),
			      buf.get_iter_at_mark(_find_state.bound))
	else:
		bounds = buf.get_selection_bounds()
	
		if not bounds:
			bounds = buf.get_bounds()

		if cmd != '':
			r = re.compile(cmd, flags)
			_find_state = FindState(r, flags, cmd, buf.create_mark(None, bounds[1], False))
		else:
			_find_state = None
			return False

	# Try to find it, go looking from bounds[0] to bounds[1], using _in_search[0]
	# as the regular expression
	text = bounds[0].get_text(bounds[1])
	ret = _find_state.regex.search(text)
	
	if not ret:
		entry.info_show('<i>Search hit end of the document</i>', True)
		buf.move_mark(buf.get_selection_bound(), buf.get_iter_at_mark(buf.get_insert()))

		_find_state = None
		return False
	else:
		start = bounds[0].copy()
		start.forward_chars(ret.start())

		end = bounds[0].copy()
		end.forward_chars(ret.end())
		
		buf.move_mark(buf.get_insert(), start)
		buf.move_mark(buf.get_selection_bound(), end)
		
		view.scroll_to_mark(buf.get_insert(), 0.2, True, 0, 0.5)
		
		entry.prompt('Search next:')
		entry.enable_continuation()
	
	return ret

def __default__(view, *args, **kwargs):
	"""Find regex in document: find.regex &lt;regex&gt;

Find text in the document that matches a given regular expression. The regular
expression syntax is that of python regular expressions."""
	return _find(view, 0, **kwargs)

def _find_insensitive(view, *args, **kwargs):
	"""Find regex in document (case insensitive): find.regex-i &lt;regex&gt;

Find text in the document that matches a given regular expression. The regular
expression syntax is that of python regular expressions. Matching dicards case."""
	return _find(view, re.IGNORECASE, **kwargs)

def _replace(view, replaceall, flags, **kwargs):
	global _find_state

	# If not search before, first search something
	entry = kwargs['_entry']
	cmd = kwargs['_cmd']
	
	if not _find_state:
		ret = _find(view, flags, **kwargs)
		
		if ret:
			entry.prompt('Replace with:')

		return True
	
	if _find_state.replace == None and not cmd:
		# Find for replacement
		entry.prompt('Replace with:')
		entry.enable_continuation()

		# Set to empty string so replacement with empty string can happen
		_find_state.replace = ''
		return True
	
	if cmd:
		_find_state.replace = cmd
	
	# Replace current selection with _find_state.replace and search for next
	view.get_buffer().begin_user_action()

	while True:
		buf = view.get_buffer()
		bounds = buf.get_selection_bounds()
	
		if bounds:
			buf.begin_user_action()
			ret = _find_state.regex.sub(_find_state.replace, bounds[0].get_text(bounds[1]))

			buf.delete(bounds[0], bounds[1])
			
			if ret:
				buf.insert(bounds[1], ret)
		
			buf.move_mark(buf.get_insert(), bounds[1])
			buf.end_user_action()

		# Search for next
		kwargs['_cmd'] = _find_state.find
	
		if not _find(view, flags, **kwargs):
			break
		
		if not replaceall:
			entry.prompt('Replace next:')
			break
	
	view.get_buffer().end_user_action()

	return not replaceall

def replace(view, *args, **kwargs):
	"""Find/replace regex in document: find.replace &lt;text&gt;

Quickly find and replace phrases in the document using regular expressions"""
	return _replace(view, False, 0, **kwargs)

def replace_i(view, *args, **kwargs):
	"""Find/replace regex in document (case insensitive): find.replace-i &lt;text&gt;

Quickly find and replace phrases in the document using regular expressions"""
	return _replace(view, False, re.IGNORECASE, **kwargs)

def replace_all(view, *args, **kwargs):
	"""Find/replace all regex in document: find.replace-all &lt;text&gt;

Quickly find and replace all phrases in the document using regular expressions"""
	return _replace(view, True, 0, **kwargs)

def replace_all_i(view, *args, **kwargs):
	"""Find/replace all regex in document: find.replace-all-i &lt;text&gt;

Quickly find and replace all phrases in the document using regular expressions"""
	return _replace(view, True, 0, **kwargs)

def __cancel_continuation__(view, cmd):
	global _find_state

	_find_state = None
