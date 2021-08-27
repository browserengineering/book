from PIL import Image, ImageTk
import numpy
import skia
import tkinter
import io

WIDTH=600
HEIGHT=800

surface = skia.Surface(WIDTH, HEIGHT)

with surface as canvas:
    canvas.save()
    canvas.translate(128., 128.)
    canvas.rotate(45.)
    rect = skia.Rect.MakeXYWH(-90.5, -90.5, 181.0, 181.0)
    paint = skia.Paint()
    paint.setColor(skia.ColorBLUE)
    canvas.drawRect(rect, paint)
    canvas.restore()

skia_image = surface.makeImageSnapshot()

# First doesn't work - messes up color channels. Second says it isn't supported.
#pil_image = Image.fromarray(skia_image.convert(alphaType=skia.kUnpremul_AlphaType))
#pil_image = Image.fromarray(skia_image, 'RGBa')

# for some reason, saving to a data file does get the channels right:
with io.BytesIO(skia_image.encodeToData()) as f:
    pil_image = Image.open(f)
    pil_image.load()

window = tkinter.Tk()
canvas = tkinter.Canvas(
    window,
    width=WIDTH,
    height=HEIGHT
)
canvas.pack()
tk_image = ImageTk.PhotoImage(image=pil_image)
canvas.create_image(0, 0, image=tk_image, anchor="nw")

tkinter.mainloop()
