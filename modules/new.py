import os
import gedit
import commander.commands as commands

__commander_module__ = True

def __default__(view, new_name):
	"""Create new file
"""
	window = view.get_toplevel()
	uri = window.get_active_document().get_uri_for_display()
	new_uri = create_file(uri, new_name)
	
	if not new_uri:
		return commands.result.HIDE
	
	window.create_tab_from_uri(new_uri, None, 0, False, True)

	return commands.result.HIDE



def create_file(uri, new_name):

	if not uri:
		return False

	base_dir = os.path.dirname(uri)
	new_uri = os.path.abspath(os.path.join(base_dir, new_name))

	if os.path.exists(new_uri):
		return False

	new_base_dir = os.path.dirname(new_uri)
	
	if os.path.exists(new_base_dir):
		if not os.path.isdir(new_base_dir):
			return False
	else:
		os.makedirs(new_base_dir)

	open(new_uri,'w').close()
	
	return 'file://' + new_uri

