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
        self.a = 1 - (1 - source.a) * (1 - self.a)
        self.r = \
            (self.r * (1 - source.a) * self.a + \
                source.r * source.a) / self.a
        self.g = \
            (self.g * (1 - source.a) * self.a + \
                source.g * source.a) / self.a
        self.b = \
            (self.b * (1 - source.a) * self.a + \
                source.b * source.a) / self.a
        return self

    def destination_in(self, source):
        self.r = self.r * self.a * source.a
        self.g = self.g * self.a * source.a
        self.b = self.b * self.a * source.a
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
        destination[x, y].difference(source[x, y])
        destination[x, y].source_over(source[x, y])
