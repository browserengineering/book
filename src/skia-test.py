from PIL import Image, ImageTk
import numpy
import skia
import tkinter
import io

WIDTH=600
HEIGHT=800

surface = skia.Surface(WIDTH, HEIGHT)

with surface as canvas:
    rect = skia.Rect.MakeXYWH(0, 0, 300, 400)
    paint = skia.Paint()
    paint.setColor(skia.ColorBLUE)
    canvas.drawRect(rect, paint)

    paint = skia.Paint(AntiAlias=True, Color=skia.ColorRED)
    canvas.drawString('String', 10, 32, skia.Font(skia.Typeface('Arial'), 36), paint)
    
    paint.setColor(skia.ColorGREEN)
    blob = skia.TextBlob('Blob', skia.Font(skia.Typeface('Times New Roman'), 36))
    canvas.drawTextBlob(blob, 10, 64, paint)
    
    paint.setColor(skia.ColorBLUE)
    blob = skia.TextBlob('Blob', skia.Font(None, 36), [(0, 0), (32, 5), (64, -5), (96, 2)])
    canvas.drawTextBlob(blob, 10, 96, paint)

skia_image = surface.makeImageSnapshot()
skia_image.save('output.png', skia.kPNG)

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
