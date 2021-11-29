import skia

# Note: this is sample code to explain the concept, it is not part
# of the actual browser.
def composite(source_color, backdrop_color, compositing_mode):
    if compositing_mode == "source-over":
        (source_r, source_g, source_b, source_a) = \
        tuple(source_color)
        (backdrop_r, backdrop_g, backdrop_b, backdrop_a) = \
            tuple(backdrop_color)
        return skia.Color4f(
            backdrop_r * (1-source_a) * backdrop_a + \
                source_r * source_a,
            backdrop_g * (1-source_a) * backdrop_a + \
                source_g * source_a,
            backdrop_b * (1-source_a) * backdrop_a + \
                source_b * source_a,
            1 - (1 - source_a) * (1 - backdrop_a))
    elif compositing_mode == "destination-in":
        (source_r, source_g, source_b, source_a) = tuple(source_color)
        (backdrop_r, backdrop_g, backdrop_b, backdrop_a) = \
             tuple(backdrop_color)
        return skia.Color4f(
            backdrop_a * source_a * backdrop_r,
            backdrop_a * source_a * backdrop_g,
            backdrop_a * source_a * backdrop_b,
            backdrop_a * source_a)

# Note: this is sample code to explain the concept, it is not part
# of the actual browser.
def apply_blend(source_color_channel,
                backdrop_color_channel, blend_mode):
    if blend_mode == "multiply":
        return source_color_channel * backdrop_color_channel
    elif blend_mode == "difference":
        return abs(backdrop_color_channel - source_color_channel)
    elif blend_mode == "normal":
        return source_color_channel

# Note: this is sample code to explain the concept, it is not part
# of the actual browser.
def blend(source_color, backdrop_color, blend_mode):
    (source_r, source_g, source_b, source_a) = tuple(source_color)
    (backdrop_r, backdrop_g, backdrop_b, backdrop_a) = \
        tuple(backdrop_color)
    return skia.Color4f(
        (1 - backdrop_a) * source_r +
            backdrop_a * apply_blend(
                source_r, backdrop_r, blend_mode),
        (1 - backdrop_a) * source_g +
            backdrop_a * apply_blend(
                source_g, backdrop_g, blend_mode),
        (1 - backdrop_a) * source_b +
            backdrop_a * apply_blend(
                source_b, backdrop_b, blend_mode),
        source_a)
