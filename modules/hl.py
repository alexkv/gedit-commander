import gtk
import gedit
import commander.commands as commands

__commander_module__ = True

def __default__(view, lang_value):
	"""Set hightlight mode
"""
	buffer = view.get_buffer()
	language_manager = gedit.get_language_manager()
	langs = language_manager.get_language_ids()
	model = gtk.ListStore(str)
	available_ids = {}
	
	for id in langs:
		lang = language_manager.get_language(id)
		name = lang.get_name()
		available_ids[name.upper()] = id
		model.append([name])
	
	lang_value = lang_value.upper()

	if available_ids.has_key(lang_value):
		lang_id = available_ids[lang_value]
		language = gedit.get_language_manager().get_language(lang_id)
		buffer.set_language(language)	
	
	return commands.result.HIDE
