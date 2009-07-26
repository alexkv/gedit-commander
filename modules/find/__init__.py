from commands import Commands
import gedit
import re
import regex

__commander_module__ = True
__aliases__ = ['/', 'find_i', '//', 'r/', 'r//']

class FindState:
	def __init__(self, find, bound):
		self.find = find
		self.bound = bound
		self.replace = None

_find_state = None

def _find(view, flags, **kwargs):
	global _find_state
	
	buf = view.get_buffer()
	cmd = kwargs['_cmd']
	entry = kwargs['_entry']
	
	if not _find_state and not cmd:
		# Ask for a search text first
		entry.prompt('Find:')
		entry.enable_continuation()
		return False

	if _find_state and (not cmd or cmd == _find_state.find):
		bounds = (buf.get_iter_at_mark(buf.get_selection_bound()),
			      buf.get_iter_at_mark(_find_state.bound))
	else:
		bounds = buf.get_selection_bounds()
	
		if not bounds:
			bounds = buf.get_bounds()

		view.get_buffer().set_search_text(cmd, flags)
	
		if cmd != '':
			_find_state = FindState(cmd, buf.create_mark(None, bounds[1], False))
		else:
			_find_state = None
			return False

	if not view.get_buffer().search_forward(bounds[0], bounds[1], bounds[0], bounds[1]):
		entry.info_show('<i>Search hit end of the document</i>', True)
		_find_state = None
		return False
	else:
		buf.move_mark(buf.get_insert(), bounds[0])
		buf.move_mark(buf.get_selection_bound(), bounds[1])
		
		view.scroll_to_mark(buf.get_insert(), 0.2, True, 0, 0.5)
		
		entry.prompt('Search next:')
		entry.enable_continuation()

		return True

def __default__(view, *args, **kwargs):
	"""Find in document: find &lt;text&gt;

Quickly find phrases in the document"""
	return _find(view, gedit.SEARCH_CASE_SENSITIVE, **kwargs)

def _find_insensitive(view, *args, **kwargs):
	"""Find in document (case insensitive): find-i &lt;text&gt;

Quickly find phrases in the document (case insensitive)"""
	return _find(view, 0, **kwargs)

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
			buf.delete(bounds[0], bounds[1])
			buf.insert(bounds[1], _find_state.replace)
		
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
	"""Find/replace in document: find.replace &lt;text&gt;

Quickly find and replace phrases in the document"""
	return _replace(view, False, gedit.SEARCH_CASE_SENSITIVE, **kwargs)

def replace_all(view, *args, **kwargs):
	"""Find/replace all in document: find.replace-all &lt;text&gt;

Quickly find and replace all phrases in the document"""
	return _replace(view, True, gedit.SEARCH_CASE_SENSITIVE, **kwargs)

def replace_all_i(view, *args, **kwargs):
	"""Find/replace all in document (case insensitive): find.replace-all-i &lt;text&gt;

Quickly find and replace all phrases in the document (case insensitive)"""
	return _replace(view, True, 0, **kwargs)
	
def replace_i(view, *args, **kwargs):
	"""Find/replace all in document (case insensitive): find.replace-i &lt;text&gt;

Quickly find and replace phrases in the document (case insensitive)"""
	return _replace(view, False, 0, **kwargs)

def __cancel_continuation__(view, cmd):
	global _find_state
	
	_find_state = None

locals()['/'] = __default__
locals()['find_i'] = _find_insensitive
locals()['//'] = replace
locals()['r/'] = regex.__default__
locals()['r//'] = regex.replace
locals()['regex_i'] = regex._find_insensitive
