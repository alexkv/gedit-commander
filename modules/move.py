import commander.commands as commands
import gtk
import re

__commander_module__ = True

def _move(view, what, num, modifier):
	try:
		num = int(num)
	except:
		raise commands.exceptions.Execute('Invalid number: ' + str(num))
		
	view.emit('move-cursor', what, num, modifier & gtk.gdk.CONTROL_MASK)
	return commands.result.HIDE

def word(view, modifier, num=1):
	return _move(view, gtk.MOVEMENT_WORDS, num, modifier)

def line(view, modifier, num=1):
	return _move(view, gtk.MOVEMENT_DISPLAY_LINES, num, modifier)

def char(view, modifier, num=1):
	return _move(view, gtk.MOVEMENT_VISUAL_POSITIONS, num, modifier)

def paragraph(view, modifier, num=1):
	return _move(view, gtk.MOVEMENT_PARAGRAPHS, num, modifier)

def regex(view, modifier, regex, num=1):
	try:
		r = re.compile(regex, re.DOTALL | re.MULTILINE | re.UNICODE)
	except Exception as e:
		raise commands.exceptions.Execute('Invalid regular expression: ' + str(e))
	
	try:
		num = int(num)
	except Exception as e:
		raise commands.exceptions.Execute('Invalid number: ' + str(e))
	
	buf = view.get_buffer()
	start = buf.get_iter_at_mark(buf.get_insert())
	
	if num > 0:
		end = buf.get_end_iter()
	else:
		end = start.copy()
		start = buf.get_start_iter()
	
	text = start.get_text(end)
	ret = list(r.finditer(text))
	
	if num < 0:
		ret.reverse()
	
	idx = min(abs(num), len(ret))
	
	if idx > 0:
		found = ret[idx - 1]
		start = buf.get_iter_at_mark(buf.get_insert())
		
		if num < 0:
			start.backward_char(len(text) - found.start(0))
		else:
			start.forward_chars(found.start(0))

		if modifier & gtk.gdk.CONTROL_MASK:
			buf.move_mark(buf.get_selection_bound(), start)
		else:
			buf.move_mark(buf.get_insert(), start)
			buf.move_mark(buf.get_selection_bound(), start)
		
		visible = view.get_visible_rect()
		loc = view.get_iter_location(start)

		# Scroll there if needed
		if loc.y + loc.height < visible.y or loc.y > visible.y + visible.height:
			view.scroll_to_mark(buf.get_insert(), 0.2, True, 0, 0.5)
	
	return commands.result.HIDE
