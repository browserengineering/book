#!/usr/bin/python3

"""

This file computes the alpha, red, green, and blue masks your computer
needs to transfer data between Skia and SDL. To do so, it draws red,
green, and blue squares, reads out the raw bytes, and computes the
masks based on that.

If you run this file, it will first print out mask values that you can
copy into your code. The output will look like this:

    ALPHA_MASK = 0xff000000
    RED_MASK = 0x000000ff
    GREEN_MASK = 0x0000ff00
    BLUE_MASK = 0x00ff0000

As a check, the code then opens a window with a red, green, and blue
square in order from left to right. If that's what you see, the mask
values output are safe to use. If you see different colors, or in a
different order, something has gone wrong; please file a bug here:

    https://github.com/browserengineering/book/issues

"""

import sdl2
import skia
import ctypes
import sys

# First, we draw red, green, and blue squares, in that order.

skia_surface = skia.Surface(300, 100)
canvas = skia_surface.getCanvas()
canvas.drawRect(skia.Rect.MakeLTRB(000, 0, 100, 100), skia.Paint(Color=skia.ColorRED))
canvas.drawRect(skia.Rect.MakeLTRB(100, 0, 200, 100), skia.Paint(Color=skia.ColorGREEN))
canvas.drawRect(skia.Rect.MakeLTRB(200, 0, 300, 100), skia.Paint(Color=skia.ColorBLUE))
skia_image = skia_surface.makeImageSnapshot()
skia_bytes = skia_image.tobytes()
r_bytes = skia_bytes[0:4]
g_bytes = skia_bytes[400:404]
b_bytes = skia_bytes[800:804]

# Next, we fix endianness, and extract the alpha mask

if sdl2.SDL_BYTEORDER != sdl2.SDL_BIG_ENDIAN:
    r_bytes = r_bytes[::-1]
    g_bytes = g_bytes[::-1]
    b_bytes = b_bytes[::-1]
a_bytes = bytes([r & g & b for r, g, b in zip(r_bytes, g_bytes, b_bytes)])
r_bytes = bytes([r - a for r, a in zip(r_bytes, a_bytes)])
g_bytes = bytes([g - a for g, a in zip(g_bytes, a_bytes)])
b_bytes = bytes([b - a for b, a in zip(b_bytes, a_bytes)])

# We print those masks out, which you can copy into your browser
    
def make_mask(x):
    return "0x" + "".join(["ff" if i else "00" for i in x])

print(f"""
ALPHA_MASK = {make_mask(a_bytes)}
RED_MASK = {make_mask(r_bytes)}
GREEN_MASK = {make_mask(g_bytes)}
BLUE_MASK = {make_mask(b_bytes)}
""")

a_mask = int(make_mask(a_bytes), 16)
r_mask = int(make_mask(r_bytes), 16)
g_mask = int(make_mask(g_bytes), 16)
b_mask = int(make_mask(b_bytes), 16)

# Finally, we display the colors using these masks, so you can verify
# that they are correct.

sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO)
sdl_window = sdl2.SDL_CreateWindow(b"Color test",
    sdl2.SDL_WINDOWPOS_CENTERED, sdl2.SDL_WINDOWPOS_CENTERED,
    300, 100, sdl2.SDL_WINDOW_SHOWN)

depth = 32
pitch = 4 * 300
sdl_surface = sdl2.SDL_CreateRGBSurfaceFrom(
    skia_bytes, 300, 100, depth, pitch,
    r_mask, g_mask, b_mask, a_mask)

sdl_rect = sdl2.SDL_Rect(0, 0, 300, 100)

window_surface = sdl2.SDL_GetWindowSurface(sdl_window)
# SDL_BlitSurface is what actually does the copy.
sdl2.SDL_BlitSurface(sdl_surface, sdl_rect, window_surface, sdl_rect)
sdl2.SDL_UpdateWindowSurface(sdl_window)

# The process will run until you close the window:

event = sdl2.SDL_Event()
while True:
    ret = sdl2.SDL_PollEvent(ctypes.byref(event))
    if ret and event.type == sdl2.SDL_QUIT:
        sdl2.SDL_Quit()
        break
