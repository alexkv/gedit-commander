import math

def set_rounded_rectangle_path(ct, x, y, width, height, radius):
	ct.move_to(x + radius, y)

	ct.arc(x + width - radius, y + radius, radius, math.pi * 1.5, math.pi * 2)
	ct.arc(x + width - radius, y + height - radius, radius, 0, math.pi * 0.5)
	ct.arc(x + radius, y + height - radius, radius, math.pi * 0.5, math.pi)
	ct.arc(x + radius, y + radius, radius, math.pi, math.pi * 1.5)
