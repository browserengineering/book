class Pixel:
    def __init__(self, r, g, b, a):
        self.r = r
        self.g = g
        self.b = b
        self.a = a

    def alphaf(self, opacity):
        self.a = self.a * opacity
        return self

    def source_over(self, source):
        new_a = source.a + self.a * (1 - source.a)
        if new_a == 0: return self
        self.r = \
            (self.r * (1 - source.a) * self.a + \
                source.r * source.a) / new_a
        self.g = \
            (self.g * (1 - source.a) * self.a + \
                source.g * source.a) / new_a
        self.b = \
            (self.b * (1 - source.a) * self.a + \
                source.b * source.a) / new_a
        self.a = new_a
        return self

    def destination_in(self, source):
        self.a = self.a * source.a
        return self

    def multiply(self, source):
        self.r = self.r * source.r
        self.g = self.g * source.g
        self.b = self.b * source.b
        return self

    def difference(self, source):
        self.r = abs(self.r - source.r)
        self.g = abs(self.g - source.g)
        self.b = abs(self.b - source.b)
        return self

    def copy(self):
        return Pixel(self.r, self.g, self.b, self.a)

    def __eq__(self, other):
        return self.r == other.r and self.g == other.g and \
            self.b == other.b and self.a == other.a

    def __repr__(self):
        return f"Pixel({self.r}, {self.g}, {self.b}, {self.a})"
    
def gray(x):
    return Pixel(x, x, x, 1.0)

def do_thing():
    for (x, y) in destination.coordinates():
        source[x, y].alphaf(opacity)
        source[x, y].difference(destination[x, y])
        destination[x, y].source_over(source[x, y])

class Opacity:
    def __init__(self, opacity, children):
        self.opacity = opacity
        self.children = children
        self.rect = skia.Rect.MakeEmpty()
        for cmd in self.children:
            self.rect.join(cmd.rect)

    def execute(self, canvas):
        paint = skia.Paint(
            Alphaf=self.opacity,
        )
        if self.opacity < 1:
            canvas.saveLayer(None, paint)
        for cmd in self.children:
            cmd.execute(canvas)
        if self.opacity < 1:
            canvas.restore()
