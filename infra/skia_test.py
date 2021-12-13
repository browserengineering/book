import sdl2
import skia
import ctypes
import sys

sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO)
sdl_window = sdl2.SDL_CreateWindow(b"Color test",
    sdl2.SDL_WINDOWPOS_CENTERED, sdl2.SDL_WINDOWPOS_CENTERED,
    300, 100, sdl2.SDL_WINDOW_SHOWN)
skia_surface = skia.Surface(300, 100)
canvas = skia_surface.getCanvas()

canvas.drawRect(skia.Rect.MakeLTRB(000, 0, 100, 100), skia.Paint(Color=skia.ColorRED))
canvas.drawRect(skia.Rect.MakeLTRB(100, 0, 200, 100), skia.Paint(Color=skia.ColorGREEN))
canvas.drawRect(skia.Rect.MakeLTRB(200, 0, 300, 100), skia.Paint(Color=skia.ColorBLUE))
skia_image = skia_surface.makeImageSnapshot()
skia_bytes = skia_image.tobytes()
print("R:", skia_bytes[0:4])
print("G:", skia_bytes[400:404])
print("B:", skia_bytes[800:804])

depth = 32
pitch = 4 * 300
if sdl2.SDL_BYTEORDER == sdl2.SDL_BIG_ENDIAN:
    red_mask = 0xff000000
    green_mask = 0x00ff0000
    blue_mask = 0x0000ff00
    alpha_mask = 0x000000ff
else:
    red_mask = 0x000000ff
    green_mask = 0x0000ff00
    blue_mask = 0x00ff0000
    alpha_mask = 0xff000000
sdl_surface = sdl2.SDL_CreateRGBSurfaceFrom(
    skia_bytes, 300, 100, depth, pitch,
    red_mask, green_mask, blue_mask, alpha_mask)

sdl_rect = sdl2.SDL_Rect(0, 0, 300, 100)

window_surface = sdl2.SDL_GetWindowSurface(sdl_window)
# SDL_BlitSurface is what actually does the copy.
sdl2.SDL_BlitSurface(sdl_surface, sdl_rect, window_surface, sdl_rect)
sdl2.SDL_UpdateWindowSurface(sdl_window)

event = sdl2.SDL_Event()
while True:
    while sdl2.SDL_PollEvent(ctypes.byref(event)) != 0:
        if event.type == sdl2.SDL_QUIT:
            sdl2.SDL_Quit()
            sys.exit()
