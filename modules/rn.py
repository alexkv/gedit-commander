import re
import gedit
import shutil
import commander.commands as commands

__commander_module__ = True

def __default__(view, new_name):
	"""Rename current file
"""
	win = view.get_toplevel()
	tab = win.get_active_tab()
	doc = tab.get_document()
	buffer = view.get_buffer()
	
	uri = doc.get_uri()
	
	if not uri:
		return commands.result.HIDE

	res = re.findall(r"^file:\/\/(\/.+?)([^\/]+?)$", uri)[0]
	line = doc.get_iter_at_mark(doc.get_insert()).get_line()
	encoding = gedit.encoding_get_current()
	win.close_tab(tab)
	
	shutil.move(res[0] + res[1], res[0] + new_name)
	
	win.create_tab_from_uri('file://' + res[0] + new_name, 
		encoding, 
		line, False, True)

	return commands.result.HIDE

def _rename_file(file):
	pass


