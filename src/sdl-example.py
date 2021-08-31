import ctypes
import sys
import sdl2
from sdl2 import *
import skia

def main():
		WIDTH=600
		HEIGHT=800
		
		SDL_Init(SDL_INIT_VIDEO)
		window = SDL_CreateWindow(b"Hello World",
				SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED,
				WIDTH, HEIGHT, SDL_WINDOW_SHOWN)
		windowsurface = SDL_GetWindowSurface(window)

		surface = skia.Surface(WIDTH, HEIGHT)
		with surface as canvas:
				canvas.clear(skia.ColorWHITE)

				rect = skia.Rect.MakeXYWH(0, 0, 200, 200)
				paint = skia.Paint()
				paint.setColor(skia.ColorRED)
				canvas.drawRect(rect, paint)

				rect = skia.Rect.MakeXYWH(200, 200, 200, 200)
				paint = skia.Paint()
				paint.setColor(skia.ColorGREEN)
				canvas.drawRect(rect, paint)

				rect = skia.Rect.MakeXYWH(400, 400, 200, 200)
				paint = skia.Paint()
				paint.setColor(skia.ColorBLUE)
				canvas.drawRect(rect, paint)

		skia_image = surface.makeImageSnapshot()
		skia_bytes = skia_image.tobytes()

		depth = 32
		pitch = 4 * WIDTH
		# Alpha is at the start for some reason - ARGB.
		rmask = 0x00ff0000
		gmask = 0x0000ff00
		bmask = 0x000000ff
		amask = 0xff000000
		rgb_surface = SDL_CreateRGBSurfaceFrom(
			skia_bytes, WIDTH, HEIGHT, depth, pitch, rmask, gmask, bmask, amask)
		src_rect = SDL_Rect(0, 0, WIDTH, HEIGHT)
		dst_rect = SDL_Rect(0, 0, WIDTH, HEIGHT)
		SDL_BlitSurface(rgb_surface, src_rect, windowsurface, src_rect)

		SDL_UpdateWindowSurface(window)

		running = True
		event = SDL_Event()
		while running:
				while SDL_PollEvent(ctypes.byref(event)) != 0:
						if event.type == SDL_QUIT:
								running = False
								break

		SDL_DestroyWindow(window)
		SDL_Quit()
		return 0

if __name__ == "__main__":
		sys.exit(main())