import commands
import types
import gtksourceview2 as gsv

__commander_module__ = True

def __default__(view, *args, **kwargs):
	"""Set gedit option: set &lt;option&gt; &lt;value&gt;

Sets a gedit option, such as document language, or indenting"""
	cmd = kwargs['_cmd'].strip()
	parts = cmd.split(' ', 1)

	name = parts[0]
	value = parts[1]

	if name in __dict__ and type(__dict__[name]) == types.FunctionType:
		kwargs['_cmd'] = value
		args = ars[1:]
		return __dict__[name](view, *args, **kwargs)
	else:
		raise commands.ExecuteException('Invalid setting: ' + name)

def language(view, *args, **kwargs):
	"""Set document language: set.language &lt;language&gt;

Set the document language to the language with the specified id"""
	cmd = kwargs['_cmd'].strip()

	if cmd == '' or cmd == 'none':
		view.get_buffer().set_language(None)
		return False

	manager = gsv.language_manager_get_default()
	lang = manager.get_language(cmd)
	
	if lang:
		view.get_buffer().set_language(lang)
		return False
	else:
		raise commands.ExecuteException('Invalid language: ' + cmd)

def tab_width(view, *args, **kwargs):
	"""Set document tab width: set.tab-width &lt;width&gt;

Set the document tab width"""
	cmd = kwargs['_cmd'].strip()
	
	try:
		cmd = int(cmd)
	except:
		raise commands.ExecuteException("Invalid tab width: " + str(cmd))
	
	if cmd <= 0:
		raise commands.ExecuteException("Invalid tab width: " + str(cmd))
	
	view.set_tab_width(cmd)
	return False

def use_spaces(view, *args, **kwargs):
	"""Use spaces instead of tabs: set.use-spaces &lt;yes/no&gt;

Set to true/yes to use spaces instead of tabs"""
	
	setting = kwargs['_cmd'].strip() in ('yes', 'true', '1')
	view.set_insert_spaces_instead_of_tabs(setting)
	
	return False

def draw_spaces(view, *args, **kwargs):
	"""Draw spaces: set.draw-spaces &lt;none/all/tabs/newlines/nbsp/spaces&gt;

Set what kind of spaces should be drawn. Multiple options can be defined, e.g.
for drawing spaces and tabs: <i>set.draw-spaces space tab</i>"""
	m = {
		'none': 0,
		'all': gsv.DRAW_SPACES_ALL,
		'tabs': gsv.DRAW_SPACES_TAB,
		'newlines': gsv.DRAW_SPACES_NEWLINE,
		'nbsp': gsv.DRAW_SPACES_NBSP,
		'spaces': gsv.DRAW_SPACES_SPACE
	}
	
	flags = 0
	
	for arg in args:
		for a in m:
			if a.startswith(arg):
				flags = flags | m[a]
		
	view.set_draw_spaces(flags)
	return False

def __autocomplete_language__(val):
	manager = gsv.language_manager_get_default()
	ids = manager.get_language_ids()
	ids.append('none')
	ids.sort()
	
	return filter(lambda x: x.startswith(val), ids)

def __autocomplete_use_spaces__(val):
	vals = ['yes', 'no']
	return filter(lambda x: x.startswith(val), vals)

def __autocomplete_draw_spaces__(val):
	vals = ['none', 'all', 'tabs', 'newlines', 'nbsp', 'spaces']
	return filter(lambda x: x.startswith(val), vals)
