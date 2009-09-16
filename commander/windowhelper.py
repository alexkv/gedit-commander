import gedit
import gtk
from entry import Entry
from info import Info

class WindowHelper:
	def __init__(self, plugin, window):
		self._window = window
		self._plugin = plugin
		self._entry = None
		
		self._accel = gtk.AccelGroup()
		self._accel.connect_group(gtk.keysyms.C, gtk.gdk.SUPER_MASK, 0, self._do_command)
		self._window.add_accel_group(self._accel)
	
	def deactivate(self):
		self._window.remove_accel_group(self._accel)
		self._window = None
		self._plugin = None

	def update_ui(self):
		pass
	
	def _do_command(self, group, obj, keyval, mod):
		view = self._window.get_active_view()
		
		if not view:
			return False

		if not self._entry:
			self._entry = Entry(self._window.get_active_view())
			self._entry.connect('destroy', self.on_entry_destroy)

		self._entry.grab_focus()
		return True
	
	def on_entry_destroy(self, widget):
		self._entry = None
