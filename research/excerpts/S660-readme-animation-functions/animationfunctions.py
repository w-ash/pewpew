# Excerpt from jackw01/led-control@8e3fe1d0456e589213ecdef1dc8ce57aa15142b6
# ledcontrol/animationfunctions.py lines 10-26, verbatim. MIT; jackw01.
# Source entry [S660]. See LICENSE-NOTE.md.
# lines 10-26
ColorMode = Enum('ColorMode', ['hsv', 'rgb'])

def blank(t, dt, x, y, z, prev_state):
    return (0, 0, 0), ColorMode.hsv

static_function_ids = [0, 1, 2, 3] # pattern IDs that display a solid color

default = {
    0: {
        'name': 'Static Color',
        'primary_speed': 0.0,
        'primary_scale': 1.0,
        'default': True,
        'source': '''
def pattern(t, dt, x, y, z, prev_state):
    return palette(0), hsv
'''
