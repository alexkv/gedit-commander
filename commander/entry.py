import gtk
import cairo
from transparentwindow import TransparentWindow
from history import History
import os
from commands import Commands
from info import Info
import glib
from xml.sax import saxutils
import commands

class Entry(TransparentWindow):
	def __init__(self, commands, view):
		TransparentWindow.__init__(self)

		self._view = view
		self._commands = commands
		
		self._entry = gtk.Entry()
		self._entry.set_name('transparent-flat-box')
		self._entry.modify_font(self._view.style.font_desc)
		self._entry.set_has_frame(False)
		self._entry.set_app_paintable(True)
		self._entry.modify_text(gtk.STATE_NORMAL, self._view.style.text[gtk.STATE_NORMAL])

		self._entry.connect('expose-event', self.on_expose_entry)
		self._entry.connect('focus-out-event', self.on_entry_focus_out)
		self._entry.connect('key-press-event', self.on_entry_key_press)
		self._entry.connect('realize', self.on_entry_realize)

		self._entry.props.can_default = True
		self.set_default(self._entry)
		self.set_focus(self._entry)
		
		self._entry.show()
		self._history = History(os.path.expanduser('~/.gnome2/gedit/commander/history'))
		
		hbox = gtk.HBox(False, 3)
		lbl = gtk.Label('<b>&gt;&gt;&gt;</b>')
		lbl.set_use_markup(True)
		lbl.modify_font(self._view.style.font_desc)
		lbl.modify_fg(gtk.STATE_NORMAL, self._view.style.text[gtk.STATE_NORMAL])
		lbl.show()
		
		self._prompt_label = lbl
		self._prompt = None
		self._default_command = None
		self._previous_command = None
		
		hbox.pack_start(lbl, False, False, 0)
		hbox.pack_start(self._entry, True, True, 0)
		hbox.show()

		self.add(hbox)
		self.set_default_size(10, 10)
		self.set_border_width(3)

		self.attach()
		self._entry.grab_focus()
		self._wait_timeout = 0
		self._info_window = None
		
		self.connect('destroy', self.on_destroy)
		
		self._history_prefix = None		
		self._running_command = None
		self._handlers = [
			[0, gtk.keysyms.Up, self.on_history_move, -1],
			[0, gtk.keysyms.Down, self.on_history_move, 1],
			[0, gtk.keysyms.Return, self.on_execute, None],
			[0, gtk.keysyms.KP_Enter, self.on_execute, None],
			[0, gtk.keysyms.Tab, self.on_complete, None],
			[0, gtk.keysyms.ISO_Left_Tab, self.on_complete, None]
		]
	
	def attach(self):
		vwwnd = self._view.get_window(gtk.TEXT_WINDOW_TEXT)
		origin = vwwnd.get_origin()
		geom = vwwnd.get_geometry()
		
		self.realize()
		
		self.move(origin[0], origin[1] + geom[3] - self.allocation.height)
		self.resize(geom[2], self.allocation.height)
	
	def background_color(self):
		bg = self._view.get_style().base[self._view.state]
		
		return [bg.red / 65535.0 * 1.1, bg.green / 65535.0 * 1.1, bg.blue / 65535.0 * 0.9, 0.8]
	
	def draw_background(self, ct):
		TransparentWindow.draw_background(self, ct)
		
		color = self.background_color()
		
		ct.move_to(0, 0)
		ct.set_line_width(1)
		ct.line_to(self.allocation.width, 0)

		ct.set_source_rgba(1 - color[0], 1 - color[1], 1 - color[2], 0.3)
		ct.stroke()
		
	def on_expose_entry(self, widget, evnt):
		ct = evnt.window.cairo_create()
		ct.save()
		
		area = evnt.area
		ct.rectangle(area.x, area.y, area.width, area.height)
		
		color = self.background_color()
		ct.set_operator(cairo.OPERATOR_SOURCE)
		ct.set_source_rgba(color[0], color[1], color[2], color[3])
		ct.fill()
		
		ct.restore()

		return False

	def on_entry_focus_out(self, widget, evnt):
		if not self._running_command:
			self.destroy()
	
	def on_entry_realize(self, widget):
		widget.window.set_back_pixmap(None, False)
		widget.window.get_children()[0].set_back_pixmap(None, False)
	
	def on_entry_key_press(self, widget, evnt):
		state = evnt.state & gtk.accelerator_get_default_mod_mask()
		text = self._entry.get_text()
		
		if evnt.keyval == gtk.keysyms.Escape and self._info_window:
			if self._running_command:
				self._running_command.cancel(self._view)

			if self._info_window:
				self._info_window.destroy()

			self._entry.set_sensitive(True)
			return True

		if evnt.keyval == gtk.keysyms.Escape and self._prompt != '':
			self.prompt()
			self._default_command = None

			return True
		elif evnt.keyval == gtk.keysyms.Escape and text == '':
			self.destroy()
			return True
		elif state == gtk.gdk.CONTROL_MASK and \
		   evnt.keyval == gtk.keysyms.c and \
		   self._entry.get_text() == '':
			self.destroy()
			return True
		
		for handler in self._handlers:
			if (handler[0] == state) and evnt.keyval == handler[1] and handler[2](handler[3]):
				return True

		if self._info_window and self._info_window.empty():
			self._info_window.destroy()
		
		self._history_prefix = None
		return False
	
	def on_history_move(self, direction):
		pos = self._entry.get_position()
		
		self._history.update(self._entry.get_text())
		
		if self._history_prefix == None:
			if len(self._entry.get_text()) == pos:
				self._history_prefix = self._entry.get_chars(0, pos)
			else:
				self._history_prefix = ''
		
		if self._history_prefix == None:
			hist = ''
		else:
			hist = self._history_prefix
			
		next = self._history.move(direction, hist)
		
		if next != None:
			self._entry.set_text(next)
			self._entry.set_position(-1)
		
		return True
	
	def enable_continuation(self, cmd=None):
		if not cmd:
			cmd = self._running_command

		self._default_command = cmd

	def prompt(self, pr=''):
		self._prompt = pr

		if not pr:
			pr = ''
		else:
			pr = ' ' + pr
		
		self._prompt_label.set_markup('<b>&gt;&gt;&gt;</b>%s' % pr)
	
	def make_info(self):
		if self._info_window == None:
			self._info_window = Info(self)
			self._info_window.show()
			
			self._info_window.connect('destroy', self.on_info_window_destroy)
	
	def on_info_window_destroy(self, widget):
		self._info_window = None
	
	def info_show(self, text='', use_markup=False):
		self.make_info()
		self._info_window.add_lines(text, use_markup)
	
	def info_status(self, text):
		self.make_info()
		self._info_window.status(text)
	
	def info_add_action(self, stock, callback, data=None):
		self.make_info()
		return self._info_window.add_action(stock, callback, data)
	
	def execute_done(self):
		if self._wait_timeout:
			glib.source_remove(self._wait_timeout)
			self._wait_timeout = 0
		else:
			self._cancel_button.destroy()
			self._cancel_button = None
			self.info_status(None)
		
		self._running_command = None
		self._entry.set_sensitive(True)
		self.command_history_done()

		if self._entry.props.has_focus or (self._info_window and not self._info_window.empty()):
			self._entry.grab_focus()
		else:
			self.destroy()
	
	def command_history_done(self):
		self._history.update(self._entry.get_text())
		self._history.add()
		self._history_prefix = None
		self._entry.set_text('')
	
	def on_wait_cancel(self):
		if self._running_command:
			self._running_command.cancel(self._view)
		
		if self._cancel_button:
			self._cancel_button.destroy()

		if self._info_window and self._info_window.empty():
			self._info_window.destroy()
			self._entry.grab_focus()
			self._entry.set_sensitive(True)			
	
	def _show_wait_cancel(self):
		self._cancel_button = self.info_add_action(gtk.STOCK_STOP, self.on_wait_cancel)
		self.info_status('<i>Waiting to finish...</i>')
		
		self._wait_timeout = 0
		return False

	def same_module(self, cmd1, cmd2):
		if cmd1.parent:
			mod1 = cmd1.parent
		else:
			mod1 = cmd1
		
		if cmd2.parent:
			mod2 = cmd2.parent
		else:
			mod2 = cmd2
		
		return mod1 == mod2

	def cancel_continuation(self, next):
		if not self._previous_command:
			return
		
		if not next or not self.same_module(self._previous_command, next):
			self._previous_command.cancel_continuation(self._view)

	def on_execute(self, dummy):
		if self._info_window:
			self._info_window.destroy()

		text = self._entry.get_text().strip()
		ret = False
		
		if text == '' and not self._default_command:
			self.prompt()
			self._entry.set_text('')
			return

		try:
			if self._default_command:
				cmd = self._default_command
				self._default_command = None

				args = self._entry.get_text()
			else:
				self._default_command = None
				cmd, args = self._commands.execute(self._entry.get_text(), self, self._view)
			
			self._running_command = cmd
			self.cancel_continuation(cmd)
			
			if cmd:
				self.prompt()
				ret = cmd.execute(self, self._view, args)
			else:
				raise commands.ExecuteException('Command not found: ' + self._entry.get_text().split(' ')[0])
		except Exception as e:
			self.command_history_done()
			
			# Show error in info
			self.info_status('<b><span color="#f66">Error:</span></b> ' + saxutils.escape(str(e)))
			return True

		self._previous_command = self._default_command

		if ret == Commands.EXECUTE_WAIT:
			# Wait for it..
			self._wait_timeout = glib.timeout_add(500, self._show_wait_cancel)
			self._entry.set_sensitive(False)
		else:
			self.command_history_done()
			self._running_command = None

			if not ret and (not self._prompt or not self._default_command) and \
			   (not self._info_window or self._info_window.empty()):
				self.destroy()
	
	def on_complete(self, dummy):
		pos = self._entry.get_position()
		text = self._entry.get_chars(0, pos)
		
		if text == '':
			return True

		res = self._commands.complete(text)
		
		if not res:
			return True
		
		if len(res) == 1:
			# Erase until the previous '.' or ' '
			f1 = text.rfind('.')
			f2 = text.rfind(' ')
			
			if f1 < f2:
				found = f2
			else:
				found = f1
			
			if found == -1:
				self._entry.delete_text(0, pos)
			else:
				self._entry.delete_text(pos - (len(text) - found) + 1, pos)
			
			newpos = self._entry.get_position()
			
			if isinstance(res[0], Commands.Method):
				nm = res[0].name
			else:
				nm = str(res[0])
			
			if not isinstance(res[0], Commands.Module) or len(res[0].commands()) == 0:
				nm = nm + " "

			if self._info_window:
				self._info_window.destroy()
			
			self._entry.insert_text(nm, newpos)
			self._entry.set_position(newpos + len(nm))
		else:
			if self._info_window:
				self._info_window.clear()
			
			ret = []
			
			for x in res:
				if isinstance(x, Commands.Method):
					ret.append('<b>' + x.name + '</b> (<i>' + x.doc() + '</i>)')
				else:
					ret.append(str(x))

			self.info_show("\n".join(ret), True)

		return True
	
	def on_destroy(self, widget):
		if self._info_window:
			self._info_window.destroy()

		if self._previous_command:
			self._previous_command.cancel_continuation(self._view)
		self._history.save()

gtk.rc_parse_string("""
style "OverrideBackground" {
	engine "pixmap" {
		image {
			function = FLAT_BOX
			detail = "entry_bg"
		}
	}
}

binding "TerminalLike" {
	unbind "<Control>A"

	bind "<Control>W" {
		"delete-from-cursor" (word-ends, -1)
	}
	bind "<Control>A" {
		"move-cursor" (buffer-ends, -1, 0)
	}
	bind "<Control>U" {
		"delete-from-cursor" (display-line-ends, -1)
	}
	bind "<Control>K" {
		"delete-from-cursor" (display-line-ends, 1)
	}
	bind "<Control>E" {
		"move-cursor" (buffer-ends, 1, 0)
	}
	bind "Escape" {
		"delete-from-cursor" (display-lines, 1)
	}
}

widget "*.transparent-flat-box" style "OverrideBackground"
widget "*.transparent-flat-box" binding "TerminalLike"
""")
