"""
This file compiles the code in Web Browser Engineering,
up to and including Chapter 16 (Reusing Previous Computations),
without exercises.
"""

import sdl2
import skia
import ctypes
import math
import OpenGL.GL
import threading
import socket
import ssl
import dukpy
import time

from lab2 import WIDTH, HEIGHT, HSTEP, VSTEP, SCROLL_STEP
from lab4 import print_tree
from lab5 import BLOCK_ELEMENTS
from lab14 import Text, Element
from lab6 import TagSelector, DescendantSelector
from lab6 import tree_to_list, INHERITED_PROPERTIES
from lab7 import CHROME_PX
from lab8 import INPUT_WIDTH_PX
from lab9 import EVENT_DISPATCH_CODE
from lab10 import COOKIE_JAR
from lab11 import FONTS, get_font, linespace, parse_blend_mode
from lab12 import MeasureTime, REFRESH_RATE_SEC
from lab12 import Task, TaskRunner, SingleThreadedTaskRunner
from lab13 import diff_styles, parse_transition, clamp_scroll, add_parent_pointers
from lab13 import absolute_bounds, absolute_bounds_for_obj
from lab13 import NumericAnimation, TranslateAnimation
from lab13 import map_translation, parse_transform, ANIMATED_PROPERTIES
from lab13 import CompositedLayer, paint_visual_effects, add_main_args
from lab13 import DrawCommand, DrawText, DrawCompositedLayer, DrawOutline, DrawLine, DrawRRect
from lab13 import VisualEffect, SaveLayer, ClipRRect, Transform
from lab14 import parse_color, parse_outline, DrawRRect, \
    paint_outline, has_outline, \
    device_px, cascade_priority, \
    is_focusable, get_tabindex, speak_text, \
    CSSParser, main_func, DrawOutline
from lab15 import URL, HTMLParser, AttributeParser, DrawImage, DocumentLayout, BlockLayout, \
    EmbedLayout, InputLayout, LineLayout, TextLayout, ImageLayout, \
    IframeLayout, JSContext, style, AccessibilityNode, Frame, Tab, \
    CommitData, Browser, BROKEN_IMAGE, font, \
    IFRAME_WIDTH_PX, IFRAME_HEIGHT_PX
import wbetools

@wbetools.patch(is_focusable)
def is_focusable(node):
    if get_tabindex(node) <= 0:
        return False
    elif "tabindex" in node.attributes:
        return True
    elif "contenteditable" in node.attributes:
        return True
    else:
        return node.tag in ["input", "button", "a"]

@wbetools.patch(print_tree)
def print_tree(node, indent=0):
    print(' ' * indent, node)
    children = node.children
    if not isinstance(children, list):
        children = children.get()
    for child in children:
        print_tree(child, indent + 2)

@wbetools.patch(tree_to_list)
def tree_to_list(tree, l):
    l.append(tree)
    children = tree.children
    if not isinstance(children, list):
        children = children.get()
    for child in children:
        tree_to_list(child, l)
    return l

@wbetools.patch(paint_outline)
def paint_outline(node, cmds, rect, zoom):
    if has_outline(node):
        thickness, color = parse_outline(node.style['outline'].get(), zoom)
        cmds.append(DrawOutline(
            rect.left(), rect.top(),
            rect.right(), rect.bottom(),
            color, thickness))

@wbetools.patch(font)
def font(notify, css_style, zoom):
    weight = css_style['font-weight'].read(notify)
    style = css_style['font-style'].read(notify)
    try:
        size = float(css_style['font-size'].read(notify)[:-2])
    except ValueError:
        size = 16
    font_size = device_px(size, zoom)
    return get_font(font_size, weight, style)

@wbetools.patch(has_outline)
def has_outline(node):
    return parse_outline(node.style['outline'].get(), 1)

@wbetools.patch(absolute_bounds_for_obj)
def absolute_bounds_for_obj(obj):
    rect = skia.Rect.MakeXYWH(
        obj.x.get(), obj.y.get(), obj.width.get(), obj.height.get())
    cur = obj.node
    while cur:
        rect = map_translation(rect, parse_transform(cur.style['transform'].get()))
        cur = cur.parent
    return rect

@wbetools.patch(paint_visual_effects)
def paint_visual_effects(node, cmds, rect):
    opacity = float(node.style["opacity"].get())
    blend_mode = parse_blend_mode(node.style["mix-blend-mode"].get())
    translation = parse_transform(node.style["transform"].get())
    border_radius = float(node.style["border-radius"].get()[:-2])
    if node.style["overflow"].get() == 'clip':
        clip_radius = border_radius
    else:
        clip_radius = 0
    needs_clip = node.style['overflow'].get() == 'clip'
    needs_blend_isolation = blend_mode != skia.BlendMode.kSrcOver or needs_clip or opacity != 1.0
    save_layer = SaveLayer(skia.Paint(BlendMode=blend_mode, Alphaf=opacity), node, [ClipRRect(rect, clip_radius, cmds, should_clip=needs_clip)], should_save=needs_blend_isolation)
    transform = Transform(translation, rect, node, [save_layer])
    node.save_layer = save_layer
    return [transform]

class ProtectedField:
    def __init__(self, obj, name, parent=None, dependencies=None,
        invalidations=None):
        self.obj = obj
        self.name = name
        self.parent = parent

        self.value = None
        self.dirty = True
        self.invalidations = set()
        self.frozen_dependencies = dependencies != None
        if dependencies != None:
            for dependency in dependencies:
                dependency.invalidations.add(self)
        else:
            assert \
                self.name in [
                    "height", "ascent", "descent", "children"
                ] or self.name in CSS_PROPERTIES

        self.frozen_invalidations = invalidations != None
        if invalidations != None:
            assert self.name == "children"
            for invalidation in invalidations:
                self.invalidations.add(invalidation)

    def set_dependencies(self, dependencies):
        assert self.name in ["height", "ascent", "descent"] or \
            self.name in CSS_PROPERTIES
        assert self.name == "height" or not self.frozen_dependencies
        for dependency in dependencies:
            dependency.invalidations.add(self)
        self.frozen_dependencies = True

    def set_ancestor_dirty_bits(self):
        parent = self.parent
        while parent and not parent.has_dirty_descendants:
            parent.has_dirty_descendants = True
            parent = parent.parent

    def mark(self):
        if self.dirty: return
        self.dirty = True
        self.set_ancestor_dirty_bits()

    def notify(self):
        for field in self.invalidations:
            field.mark()
        self.set_ancestor_dirty_bits()

    def set(self, value):
        # if self.value != None:
        #     print("Change", self)
        if value != self.value:
            self.notify()
        self.value = value
        self.dirty = False

    def get(self):
        assert not self.dirty
        return self.value

    def read(self, notify):
        if notify.frozen_dependencies or self.frozen_invalidations:
            assert notify in self.invalidations
        else:
            self.invalidations.add(notify)

        if wbetools.PRINT_INVALIDATION_DEPENDENCIES:
            prefix = ""
            if notify.obj == self.obj:
                prefix = "self."
            elif self.obj == notify.parent:
                prefix = "self.parent."
            elif notify.obj == self.obj.parent:
                prefix = "self.child."
            elif hasattr(notify.obj, "previous") and \
                notify.obj.previous == self.obj:
                    prefix = "self.previous."
            print("{} depends on {}{}".format(
                notify.name, prefix, self.name))

        return self.get()

    def copy(self, field):
        self.set(field.read(notify=self))

    def __str__(self):
        if self.dirty:
            return "<dirty>"
        else:
            return str(self.value)

    def __repr__(self):
        return "ProtectedField({}, {})".format(
            self.obj.node if hasattr(self.obj, "node") else self.obj,
            self.name)
    
CSS_PROPERTIES = {
    "font-size": "inherit", "font-weight": "inherit",
    "font-style": "inherit", "color": "inherit",
    "opacity": "1.0", "transition": "",
    "transform": "none", "mix-blend-mode": "normal",
    "border-radius": "0px", "overflow": "visible",
    "outline": "none", "background-color": "transparent",
    "image-rendering": "auto",
}

@wbetools.patch(Element)
class Element:
    def __init__(self, tag, attributes, parent):
        self.tag = tag
        self.attributes = attributes
        self.children = []
        self.parent = parent

        self.style = None
        self.animations = {}

        self.is_focused = False
        self.layout_object = None

@wbetools.patch(Text)
class Text:
    def __init__(self, text, parent):
        self.text = text
        self.children = []
        self.parent = parent

        self.style = None
        self.animations = {}

        self.is_focused = False
        self.layout_object = None

@wbetools.patch(DocumentLayout)
class DocumentLayout:
    def __init__(self, node, frame):
        self.node = node
        self.frame = frame
        node.layout_object = self
        self.parent = None
        self.previous = None
        self.children = []

        self.zoom = ProtectedField(self, "zoom", None, [])
        self.width = ProtectedField(self, "width", None, [])
        self.x = ProtectedField(self, "x", None, [])
        self.y = ProtectedField(self, "y", None, [])
        self.height = ProtectedField(self, "height")

        self.has_dirty_descendants = True

    def layout_needed(self):
        if self.zoom.dirty: return True
        if self.width.dirty: return True
        if self.height.dirty: return True
        if self.x.dirty: return True
        if self.y.dirty: return True
        if self.has_dirty_descendants: return True
        return False

    def layout(self, width, zoom):
        if not self.layout_needed(): return

        self.zoom.set(zoom)
        self.width.set(width - 2 * device_px(HSTEP, zoom))

        if not self.children:
            child = BlockLayout(self.node, self, None, self.frame)
            self.height.set_dependencies([child.height])
        else:
            child = self.children[0]
        self.children = [child]

        self.x.set(device_px(HSTEP, zoom))
        self.y.set(device_px(VSTEP, zoom))

        child.layout()
        self.has_dirty_descendants = False

        child_height = child.height.read(notify=self.height)
        self.height.set(child_height + 2 * device_px(VSTEP, zoom))

        if wbetools.ASSERT_LAYOUT_CLEAN:
            for obj in tree_to_list(self, []):
                assert not obj.layout_needed()

    def paint(self, display_list, dark_mode, scroll):
        cmds = []
        self.children[0].paint(cmds)
        if scroll != None and scroll != 0:
            rect = skia.Rect.MakeLTRB(
                self.x.get(), self.y.get(),
                self.x.get() + self.width.get(), self.y.get() + self.height.get())
            cmds = [Transform((0, -scroll), rect, self.node, cmds)]

        display_list.extend(cmds)


@wbetools.patch(BlockLayout)
class BlockLayout:
    def __init__(self, node, parent, previous, frame):
        self.node = node
        node.layout_object = self
        self.parent = parent
        self.previous = previous
        self.frame = frame

        self.zoom = ProtectedField(self, "zoom", self.parent,
            [self.parent.zoom])
        self.width = ProtectedField(self, "width", self.parent,
            [self.parent.width])
        self.height = ProtectedField(self, "height", self.parent)
        self.x = ProtectedField(self, "x", self.parent, [self.parent.x])

        if self.previous:
            y_dependencies = [self.previous.y, self.previous.height]
        else:
            y_dependencies = [self.parent.y]
        self.y = ProtectedField(self, "y", self.parent, y_dependencies)

        self.children = ProtectedField(self, "children", self.parent, None,
            [self.height])

        self.has_dirty_descendants = True

    def layout_needed(self):
        if self.zoom.dirty: return True
        if self.width.dirty: return True
        if self.height.dirty: return True
        if self.x.dirty: return True
        if self.y.dirty: return True
        if self.children.dirty: return True
        if self.has_dirty_descendants: return True
        return False

    def layout(self):
        if not self.layout_needed(): return

        self.zoom.copy(self.parent.zoom)
        self.width.copy(self.parent.width)
        self.x.copy(self.parent.x)

        if self.previous:
            prev_y = self.previous.y.read(notify=self.y)
            prev_height = self.previous.height.read(notify=self.y)
            self.y.set(prev_y + prev_height)
        else:
            self.y.copy(self.parent.y)

        mode = self.layout_mode()
        if mode == "block":
            if self.children.dirty:
                children = []
                previous = None
                for child in self.node.children:
                    next = BlockLayout(
                        child, self, previous, self.frame)
                    children.append(next)
                    previous = next
                self.children.set(children)

                height_dependencies = \
                   [child.height for child in children]
                height_dependencies.append(self.children)
                self.height.set_dependencies(height_dependencies)
        else:
            if self.children.dirty:
                self.temp_children = []
                self.new_line()
                self.recurse(self.node)
                self.children.set(self.temp_children)

                height_dependencies = \
                   [child.height for child in self.temp_children]
                height_dependencies.append(self.children)
                self.height.set_dependencies(height_dependencies)
                self.temp_children = None

        for child in self.children.get():
            child.layout()

        self.has_dirty_descendants = False

        children = self.children.read(notify=self.height)
        new_height = sum([
            child.height.read(notify=self.height)
            for child in children
        ])
        self.height.set(new_height)

    def input(self, node):
        zoom = self.zoom.read(notify=self.children)
        w = device_px(INPUT_WIDTH_PX, zoom)
        self.add_inline_child(node, w, InputLayout, self.frame)

    def image(self, node):
        zoom = self.zoom.read(notify=self.children)
        if 'width' in node.attributes:
            w = device_px(int(node.attributes['width']), zoom)
        else:
            w = device_px(node.image.width(), zoom)
        self.add_inline_child(node, w, ImageLayout, self.frame)

    def iframe(self, node):
        zoom = self.zoom.read(notify=self.children)
        if 'width' in self.node.attributes:
            w = device_px(int(self.node.attributes['width']), zoom)
        else:
            w = IFRAME_WIDTH_PX + device_px(2, zoom)
        self.add_inline_child(node, w, IframeLayout, self.frame)

    def word(self, node, word):
        zoom = self.zoom.read(notify=self.children)
        node_font = font(self.children, node.style, zoom)
        w = node_font.measureText(word)
        self.add_inline_child(
            node, w, TextLayout, self.frame, word)

    def new_line(self):
        self.previous_word = None
        self.cursor_x = 0
        last_line = self.temp_children[-1] \
            if self.temp_children else None
        new_line = LineLayout(self.node, self, last_line)
        self.temp_children.append(new_line)

    def add_inline_child(self, node, w, child_class,
        frame, word=None):
        width = self.width.read(notify=self.children)
        if self.cursor_x + w > width:
            self.new_line()
        line = self.temp_children[-1]
        if word:
            child = child_class(node, line, self.previous_word, word)
        else:
            child = child_class(node, line, self.previous_word, frame)
        line.children.append(child)
        self.previous_word = child
        zoom = self.zoom.read(notify=self.children)
        self.cursor_x += w + font(self.children, node.style, zoom).measureText(' ')

    def paint(self, display_list):
        cmds = []

        rect = skia.Rect.MakeLTRB(
            self.x.get(), self.y.get(), self.x.get() + self.width.get(),
            self.y.get() + self.height.get())

        is_atomic = not isinstance(self.node, Text) and \
            (self.node.tag == "input" or self.node.tag == "button")

        if not is_atomic:
            bgcolor = self.node.style["background-color"].get()
            if bgcolor != "transparent":
                radius = device_px(
                    float(self.node.style["border-radius"].get()[:-2]),
                    self.zoom.get())
                cmds.append(DrawRRect(rect, radius, bgcolor))
 
        for child in self.children.get():
            child.paint(cmds)

        if self.node.is_focused \
            and "contenteditable" in self.node.attributes:
            text_nodes = [
                t for t in tree_to_list(self, [])
                if isinstance(t, TextLayout)
            ]
            if text_nodes:
                cmds.append(DrawCursor(text_nodes[-1],
                    text_nodes[-1].width.get()))
            else:
                cmds.append(DrawCursor(self, 0))

        if not is_atomic:
            cmds = paint_visual_effects(self.node, cmds, rect)
        display_list.extend(cmds)

def DrawCursor(elt, offset):
    x = elt.x.get() + offset
    return DrawLine(x, elt.y.get(), x, elt.y.get() + elt.height.get(), "black", 1)

@wbetools.patch(LineLayout)
class LineLayout:
    def __init__(self, node, parent, previous):
        self.node = node
        self.parent = parent
        self.previous = previous
        self.children = []
        self.zoom = ProtectedField(self, "zoom", self.parent,
            [self.parent.zoom])
        self.x = ProtectedField(self, "x", self.parent,
            [self.parent.x])
        if self.previous:
            y_dependencies = [self.previous.y, self.previous.height]
        else:
            y_dependencies = [self.parent.y]
        self.y = ProtectedField(self, "y", self.parent,
            y_dependencies)
        self.initialized_fields = False
        self.ascent = ProtectedField(self, "ascent", self.parent)
        self.descent = ProtectedField(self, "descent", self.parent)
        self.width = ProtectedField(self, "width", self.parent,
            [self.parent.width])
        self.height = ProtectedField(self, "height", self.parent,
            [self.ascent, self.descent])

        self.has_dirty_descendants = True

    def layout_needed(self):
        if self.zoom.dirty: return True
        if self.width.dirty: return True
        if self.height.dirty: return True
        if self.x.dirty: return True
        if self.y.dirty: return True
        if self.ascent.dirty: return True
        if self.descent.dirty: return True
        if self.has_dirty_descendants: return True
        return False

    def layout(self):
        if not self.initialized_fields:
            self.ascent.set_dependencies(
               [child.ascent for child in self.children])
            self.descent.set_dependencies(
               [child.descent for child in self.children])
            self.initialized_fields = True

        if not self.layout_needed(): return

        self.zoom.copy(self.parent.zoom)
        self.width.copy(self.parent.width)
        self.x.copy(self.parent.x)
        if self.previous:
            prev_y = self.previous.y.read(notify=self.y)
            prev_height = self.previous.height.read(notify=self.y)
            self.y.set(prev_y + prev_height)
        else:
            self.y.copy(self.parent.y)

        for word in self.children:
            word.layout()

        if not self.children:
            self.ascent.set(0)
            self.descent.set(0)
            self.height.set(0)
            self.has_dirty_descendants = False
            return

        self.ascent.set(max([
            -child.ascent.read(notify=self.ascent)
            for child in self.children
        ]))

        self.descent.set(max([
            child.descent.read(notify=self.descent)
            for child in self.children
        ]))

        for child in self.children:
            new_y = self.y.read(notify=child.y)
            new_y += self.ascent.read(notify=child.y)
            new_y += child.ascent.read(notify=child.y)
            child.y.set(new_y)

        max_ascent = self.ascent.read(notify=self.height)
        max_descent = self.descent.read(notify=self.height)

        self.height.set(max_ascent + max_descent)

        self.has_dirty_descendants = False

    def paint(self, display_list):
        outline_rect = skia.Rect.MakeEmpty()
        outline_node = None
        for child in self.children:
            node = child.node
            if isinstance(node, Text) and has_outline(node.parent):
                outline_node = node.parent
                outline_rect.join(child.rect())
            child.paint(display_list)
        if outline_node:
            paint_outline(outline_node, display_list, outline_rect, self.zoom.get())

@wbetools.patch(TextLayout)
class TextLayout:
    def __init__(self, node, parent, previous, word):
        self.node = node
        self.word = word
        self.children = []
        self.parent = parent
        self.previous = previous

        self.zoom = ProtectedField(self, "zoom", self.parent,
            [self.parent.zoom])
        self.font = ProtectedField(self, "font", self.parent,
            [self.zoom,
             self.node.style['font-weight'],
             self.node.style['font-style'],
             self.node.style['font-size']])
        self.width = ProtectedField(self, "width", self.parent,
            [self.font])
        self.height = ProtectedField(self, "height", self.parent,
            [self.font])
        self.ascent = ProtectedField(self, "ascent", self.parent,
            [self.font])
        self.descent = ProtectedField(self, "descent", self.parent,
            [self.font])
        if self.previous:
            x_dependencies = [self.previous.x, self.previous.font,
            self.previous.width]
        else:
            x_dependencies = [self.parent.x]
        self.x = ProtectedField(self, "x", self.parent,
            x_dependencies)
        self.y = ProtectedField(self, "y", self.parent,
            [self.ascent, self.parent.y, self.parent.ascent])

        self.has_dirty_descendants = True

    def layout_needed(self):
        if self.zoom.dirty: return True
        if self.width.dirty: return True
        if self.height.dirty: return True
        if self.x.dirty: return True
        if self.y.dirty: return True
        if self.ascent.dirty: return True
        if self.descent.dirty: return True
        if self.font.dirty: return True
        if self.has_dirty_descendants: return True
        return False

    def layout(self):
        if not self.layout_needed(): return

        self.zoom.copy(self.parent.zoom)

        zoom = self.zoom.read(notify=self.font)
        self.font.set(font(self.font, self.node.style, zoom))

        f = self.font.read(notify=self.width)
        self.width.set(f.measureText(self.word))

        f = self.font.read(notify=self.ascent)
        self.ascent.set(f.getMetrics().fAscent * 1.25)

        f = self.font.read(notify=self.descent)
        self.descent.set(f.getMetrics().fDescent * 1.25)

        f = self.font.read(notify=self.height)
        self.height.set(linespace(f) * 1.25)

        if self.previous:
            prev_x = self.previous.x.read(notify=self.x)
            prev_font = self.previous.font.read(notify=self.x)
            prev_width = self.previous.width.read(notify=self.x)
            self.x.set(
                prev_x + prev_font.measureText(' ') + prev_width)
        else:
            self.x.copy(self.parent.x)

        self.has_dirty_descendants = False

    def paint(self, display_list):
        leading = self.height.get() / 1.25 * .25 / 2
        color = self.node.style['color'].get()
        display_list.append(DrawText(self.x.get(), self.y.get() + leading, self.word, self.font.get(), color))

    def rect(self):
        return skia.Rect.MakeLTRB(
            self.x.get(), self.y.get(), self.x.get() + self.width.get(),
            self.y.get() + self.height.get())


@wbetools.patch(EmbedLayout)
class EmbedLayout:
    def __init__(self, node, parent, previous, frame):
        self.node = node
        self.frame = frame
        node.layout_object = self
        self.parent = parent
        self.previous = previous

        self.children = []
        self.zoom = ProtectedField(self, "zoom", self.parent,
            [self.parent.zoom])
        self.font = ProtectedField(self, "font", self.parent,
           [self.zoom,
            self.node.style['font-weight'],
            self.node.style['font-style'],
            self.node.style['font-size']])
        self.width = ProtectedField(self, "width", self.parent,
            [self.zoom])
        self.height = ProtectedField(self, "height", self.parent,
            [self.zoom, self.font, self.width])
        self.ascent = ProtectedField(self, "ascent", self.parent,
            [self.height])
        self.descent = ProtectedField(self, "descent", self.parent, [])
        if self.previous:
            x_dependencies = [self.previous.x, self.previous.font, self.previous.width]
        else:
            x_dependencies = [self.parent.x]
        self.x = ProtectedField(self, "x", self.parent, x_dependencies)
        self.y = ProtectedField(self, "y", self.parent,
            [self.ascent,self.parent.y, self.parent.ascent])

        self.has_dirty_descendants = True

    def layout_needed(self):
        if self.zoom.dirty: return True
        if self.width.dirty: return True
        if self.height.dirty: return True
        if self.x.dirty: return True
        if self.y.dirty: return True
        if self.ascent.dirty: return True
        if self.descent.dirty: return True
        if self.font.dirty: return True
        if self.has_dirty_descendants: return True
        return False

    def layout_before(self):
        self.zoom.copy(self.parent.zoom)

        zoom = self.zoom.read(notify=self.font)
        self.font.set(font(self.font, self.node.style, zoom))

        if self.previous:
            assert hasattr(self, "previous")
            prev_x = self.previous.x.read(notify=self.x)
            prev_font = self.previous.font.read(notify=self.x)
            prev_width = self.previous.width.read(notify=self.x)
            self.x.set(prev_x + prev_font.measureText(' ') + prev_width)
        else:
            self.x.copy(self.parent.x)

    def layout_after(self):
        height = self.height.read(notify=self.ascent)
        self.ascent.set(-height)

        self.descent.set(0)

        self.has_dirty_descendants = False

@wbetools.patch(InputLayout)
class InputLayout(EmbedLayout):
    def layout(self):
        if not self.layout_needed(): return
        self.layout_before()
        zoom = self.zoom.read(notify=self.width)
        self.width.set(device_px(INPUT_WIDTH_PX, zoom))
        font = self.font.read(notify=self.height)
        self.height.set(linespace(font))
        self.layout_after()

    def paint(self, display_list):
        cmds = []

        rect = skia.Rect.MakeLTRB(
            self.x.get(), self.y.get(), self.x.get() + self.width.get(),
            self.y.get() + self.height.get())

        bgcolor = self.node.style["background-color"].get()
        if bgcolor != "transparent":
            radius = device_px(
                float(self.node.style["border-radius"].get()[:-2]),
                self.zoom.get())
            cmds.append(DrawRRect(rect, radius, bgcolor))

        if self.node.tag == "input":
            text = self.node.attributes.get("value", "")
        elif self.node.tag == "button":
            if len(self.node.children) == 1 and \
               isinstance(self.node.children[0], Text):
                text = self.node.children[0].text
            else:
                print("Ignoring HTML contents inside button")
                text = ""

        color = self.node.style["color"].get()
        cmds.append(DrawText(self.x.get(), self.y.get(),
                             text, self.font.get(), color))

        if self.node.is_focused and self.node.tag == "input":
            cmds.append(DrawCursor(self, self.font.get().measureText(text)))

        cmds = paint_visual_effects(self.node, cmds, rect)
        paint_outline(self.node, cmds, rect, self.zoom.get())
        display_list.extend(cmds)

@wbetools.patch(ImageLayout)
class ImageLayout(EmbedLayout):
    def layout(self):
        if not self.layout_needed(): return
        self.layout_before()
        width_attr = self.node.attributes.get('width')
        height_attr = self.node.attributes.get('height')
        image_width = self.node.image.width()
        image_height = self.node.image.height()
        aspect_ratio = image_width / image_height

        w_zoom = self.zoom.read(notify=self.width)
        h_zoom = self.zoom.read(notify=self.height)
        if width_attr and height_attr:
            self.width.set(device_px(int(width_attr), w_zoom))
            self.img_height = device_px(int(height_attr), h_zoom)
        elif width_attr:
            self.width.set(device_px(int(width_attr), w_zoom))
            w = self.width.read(notify=self.height)
            self.img_height = w / aspect_ratio
        elif height_attr:
            self.img_height = device_px(int(height_attr), h_zoom)
            self.width.set(self.img_height * aspect_ratio)
        else:
            self.width.set(device_px(image_width, w_zoom))
            self.img_height = device_px(image_height, h_zoom)
        font = self.font.read(notify=self.height)
        self.height.set(max(self.img_height, linespace(font)))
        self.layout_after()

    def paint(self, display_list):
        cmds = []
        rect = skia.Rect.MakeLTRB(
            self.x.get(),
            self.y.get() + self.height.get() - self.img_height,
            self.x.get() + self.width.get(),
            self.y.get() + self.height.get())
        quality = self.node.style["image-rendering"].get()
        cmds.append(DrawImage(self.node.image, rect, quality))
        display_list.extend(cmds)

@wbetools.patch(IframeLayout)
class IframeLayout(EmbedLayout):
    def layout(self):
        if not self.layout_needed(): return
        self.layout_before()
        width_attr = self.node.attributes.get('width')
        height_attr = self.node.attributes.get('height')
        
        w_zoom = self.zoom.read(notify=self.width)
        if width_attr:
            self.width.set(device_px(int(width_attr) + 2, w_zoom))
        else:
            self.width.set(device_px(IFRAME_WIDTH_PX + 2, w_zoom))

        zoom = self.zoom.read(notify=self.height)
        if height_attr:
            self.height.set(device_px(int(height_attr) + 2, zoom))
        else:
            self.height.set(device_px(IFRAME_HEIGHT_PX + 2, zoom)) 

        if self.node.frame:
            self.node.frame.frame_height = \
                self.height.get() - device_px(2, self.zoom.get())
            self.node.frame.frame_width = \
                self.width.get() - device_px(2, self.zoom.get())
            self.node.frame.document.width.mark()
        self.layout_after()

    def paint(self, display_list):
        frame_cmds = []
        rect = skia.Rect.MakeLTRB(self.x.get(), self.y.get(), self.x.get() + self.width.get(), self.y.get() + self.height.get())
        bgcolor = self.node.style["background-color"].get()
        if bgcolor != 'transparent':
            radius = device_px(float(self.node.style["border-radius"].get()[:-2]), self.zoom.get())
            frame_cmds.append(DrawRRect(rect, radius, bgcolor))
        if self.node.frame:
            self.node.frame.paint(frame_cmds)
        diff = device_px(1, self.zoom.get())
        offset = (self.x.get() + diff, self.y.get() + diff)
        cmds = [Transform(offset, rect, self.node, frame_cmds)]
        inner_rect = skia.Rect.MakeLTRB(self.x.get() + diff, self.y.get() + diff, self.x.get() + self.width.get() - diff, self.y.get() + self.height.get() - diff)
        cmds = paint_visual_effects(self.node, cmds, inner_rect)
        paint_outline(self.node, cmds, rect, self.zoom.get())
        display_list.extend(cmds)

def init_style(node):
    node.style = dict([
            (property, ProtectedField(node, property, None,
                [node.parent.style[property]] \
                    if node.parent and \
                        property in INHERITED_PROPERTIES \
                    else []))
            for property in CSS_PROPERTIES
        ])

@wbetools.patch(style)
def style(node, rules, frame):
    if not node.style:
        init_style(node)
    needs_style = any([field.dirty for field in node.style.values()])
    if needs_style:
        old_style = dict([
            (property, field.value)
            for property, field in node.style.items()
        ])
        new_style = CSS_PROPERTIES.copy()
        for property, default_value in INHERITED_PROPERTIES.items():
            if node.parent:
                parent_field = node.parent.style[property]
                parent_value = \
                    parent_field.read(notify=node.style[property])
                new_style[property] = parent_value
            else:
                new_style[property] = default_value
        for media, selector, body in rules:
            if media:
                if (media == 'dark') != frame.tab.dark_mode: continue
            if not selector.matches(node): continue
            for property, value in body.items():
                new_style[property] = value
        if isinstance(node, Element) and 'style' in node.attributes:
            pairs = CSSParser(node.attributes['style']).body()
            for property, value in pairs.items():
                new_style[property] = value
        if new_style["font-size"].endswith("%"):
            if node.parent:
                parent_field = node.parent.style["font-size"]
                parent_font_size = \
                    parent_field.read(notify=node.style["font-size"])
            else:
                parent_font_size = INHERITED_PROPERTIES["font-size"]
            node_pct = float(new_style["font-size"][:-1]) / 100
            parent_px = float(parent_font_size[:-2])
            new_style["font-size"] = str(node_pct * parent_px) + "px"
        if old_style:
            transitions = diff_styles(old_style, new_style)
            for property, (old_value, new_value, num_frames) in transitions.items():
                if property in ANIMATED_PROPERTIES:
                    frame.set_needs_render()
                    AnimationClass = ANIMATED_PROPERTIES[property]
                    animation = AnimationClass(old_value, new_value, num_frames)
                    node.animations[property] = animation
                    new_style[property] = animation.animate()
        for property, field in node.style.items():
            field.set(new_style[property])

    for child in node.children:
        style(child, rules, frame)

def dirty_style(node):
    for property, value in node.style.items():
        value.mark()

@wbetools.patch(JSContext)
class JSContext:
    def innerHTML_set(self, handle, s, window_id):
        frame = self.tab.window_id_to_frame[window_id]        
        self.throw_if_cross_origin(frame)
        doc = HTMLParser(
            "<html><body>" + s + "</body></html>").parse()
        new_nodes = doc.children[0].children
        elt = self.handle_to_node[handle]
        elt.children = new_nodes
        for child in elt.children:
            child.parent = elt
        obj = elt.layout_object
        if obj:
            while not isinstance(obj, BlockLayout):
                obj = obj.parent
            obj.children.mark()
        frame.set_needs_render()

    def setAttribute(self, handle, attr, value, window_id):
        frame = self.tab.window_id_to_frame[window_id]        
        self.throw_if_cross_origin(frame)
        elt = self.handle_to_node[handle]
        elt.attributes[attr] = value
        obj = elt.layout_object
        if isinstance(obj, IframeLayout) or \
           isinstance(obj, ImageLayout):
            if attr == "width" or attr == "height":
                obj.width.mark()
                obj.height.mark()
        self.tab.set_needs_render_all_frames()

    def style_set(self, handle, s, window_id):
        frame = self.tab.window_id_to_frame[window_id]
        self.throw_if_cross_origin(frame)
        elt = self.handle_to_node[handle]
        elt.attributes['style'] = s
        dirty_style(elt)
        frame.set_needs_render()

@wbetools.patch(Frame)
class Frame:
    def load(self, url, body=None):
        self.zoom = 1
        self.scroll = 0
        self.scroll_changed_in_frame = True
        headers, body = url.request(self.url, body)
        body = body.decode("utf8")
        self.url = url

        self.allowed_origins = None
        if "content-security-policy" in headers:
           csp = headers["content-security-policy"].split()
           if len(csp) > 0 and csp[0] == "default-src":
               self.allowed_origins = csp[1:]

        self.nodes = HTMLParser(body).parse()

        self.js = self.tab.get_js(url.origin())
        self.js.add_window(self)

        scripts = [node.attributes["src"] for node
                   in tree_to_list(self.nodes, [])
                   if isinstance(node, Element)
                   and node.tag == "script"
                   and "src" in node.attributes]
        for script in scripts:
            script_url = url.resolve(script)
            if not self.allowed_request(script_url):
                print("Blocked script", script, "due to CSP")
                continue

            header, body = script_url.request(url)
            body = body.decode("utf8")
            task = Task(self.js.run, script_url, body,
                self.window_id)
            self.tab.task_runner.schedule_task(task)

        self.rules = self.default_style_sheet.copy()
        links = [node.attributes["href"]
                 for node in tree_to_list(self.nodes, [])
                 if isinstance(node, Element)
                 and node.tag == "link"
                 and "href" in node.attributes
                 and node.attributes.get("rel") == "stylesheet"]
        for link in links:  
            style_url = url.resolve(link)
            if not self.allowed_request(style_url):
                print("Blocked style", link, "due to CSP")
                continue
            try:
                header, body = style_url.request(url)
            except:
                continue
            self.rules.extend(CSSParser(body.decode("utf8")).parse())

        images = [node
            for node in tree_to_list(self.nodes, [])
            if isinstance(node, Element)
            and node.tag == "img"]
        for img in images:
            try:
                src = img.attributes.get("src", "")
                image_url = url.resolve(src)
                assert self.allowed_request(image_url), \
                    "Blocked load of " + image_url + " due to CSP"
                header, body = image_url.request(url)
                img.encoded_data = body
                data = skia.Data.MakeWithoutCopy(body)
                img.image = skia.Image.MakeFromEncoded(data)
                assert img.image, "Failed to recognize image format for " + image_url
            except Exception as e:
                print("Exception loading image: url="
                    + image_url + " exception=" + str(e))
                img.image = BROKEN_IMAGE

        iframes = [node
                   for node in tree_to_list(self.nodes, [])
                   if isinstance(node, Element)
                   and node.tag == "iframe"
                   and "src" in node.attributes]
        for iframe in iframes:
            document_url = url.resolve(iframe.attributes["src"])
            if not self.allowed_request(document_url):
                print("Blocked iframe", document_url, "due to CSP")
                iframe.frame = None
                continue
            iframe.frame = Frame(self.tab, self, iframe)
            iframe.frame.load(document_url)

        self.document = DocumentLayout(self.nodes, self)
        self.set_needs_render()

    def render(self):
        if self.needs_style:
            if self.tab.dark_mode:
                INHERITED_PROPERTIES["color"] = "white"
            else:
                INHERITED_PROPERTIES["color"] = "black"
            style(self.nodes,
                  sorted(self.rules,
                         key=cascade_priority), self)
            self.needs_layout = True
            self.needs_style = False

        if self.needs_layout:
            self.document.layout(self.frame_width, self.tab.zoom)
            if self.tab.accessibility_is_on:
                self.tab.needs_accessibility = True
            else:
                self.needs_paint = True
            self.needs_layout = False

        clamped_scroll = self.clamp_scroll(self.scroll)
        if clamped_scroll != self.scroll:
            self.scroll_changed_in_frame = True
        self.scroll = clamped_scroll

    def keypress(self, char):
        if self.tab.focus and self.tab.focus.tag == "input":
            if not "value" in self.tab.focus.attributes:
                self.activate_element(self.tab.focus)
            if self.js.dispatch_event(
                "keydown", self.tab.focus, self.window_id): return
            self.tab.focus.attributes["value"] += char
            self.set_needs_render()
        elif self.tab.focus and \
            "contenteditable" in self.tab.focus.attributes:
            text_nodes = [
               t for t in tree_to_list(self.tab.focus, [])
               if isinstance(t, Text)
            ]
            if text_nodes:
                last_text = text_nodes[-1]
            else:
                last_text = Text("", self.tab.focus)
                self.tab.focus.children.append(last_text)
            last_text.text += char
            obj = self.tab.focus.layout_object
            while not isinstance(obj, BlockLayout):
                obj = obj.parent
            obj.children.mark()
            self.set_needs_render()

    def scroll_to(self, elt):
        assert not (self.needs_style or self.needs_layout)
        objs = [
            obj for obj in tree_to_list(self.document, [])
            if obj.node == self.tab.focus
        ]
        if not objs: return
        obj = objs[0]

        if self.scroll < obj.y.get() < self.scroll + self.frame_height:
            return
        new_scroll = obj.y.get() - SCROLL_STEP
        self.scroll = self.clamp_scroll(new_scroll)
        self.scroll_changed_in_frame = True
        self.set_needs_render()

    def clamp_scroll(self, scroll):
        height = math.ceil(self.document.height.get())
        maxscroll = height - self.frame_height
        return max(0, min(scroll, maxscroll))

    def focus_element(self, node):
        if node and node != self.tab.focus:
            self.needs_focus_scroll = True
        if self.tab.focus:
            self.tab.focus.is_focused = False
            dirty_style(self.tab.focus)
        if self.tab.focused_frame and self.tab.focused_frame != self:
            self.tab.focused_frame.set_needs_render()
        self.tab.focus = node
        self.tab.focused_frame = self
        if node:
            node.is_focused = True
            dirty_style(node)
        self.set_needs_render()

    def click(self, x, y):
        self.focus_element(None)
        y += self.scroll
        loc_rect = skia.Rect.MakeXYWH(x, y, 1, 1)
        objs = [obj for obj in tree_to_list(self.document, [])
                if absolute_bounds_for_obj(obj).intersects(
                    loc_rect)]
        if not objs: return
        elt = objs[-1].node
        if elt and self.js.dispatch_event(
            "click", elt, self.window_id): return
        while elt:
            if isinstance(elt, Text):
                pass
            elif elt.tag == "iframe":
                new_x = x - elt.layout_object.x.get()
                new_y = y - elt.layout_object.y.get()
                elt.frame.click(new_x, new_y)
                return
            elif is_focusable(elt):
                self.focus_element(elt)
                self.activate_element(elt)
                self.set_needs_render()
                return
            elt = elt.parent


@wbetools.patch(Tab)
class Tab:
    def zoom_by(self, increment):
        if increment > 0:
            self.zoom *= 1.1
        else:
            self.zoom *= 1 / 1.1
        for id, frame in self.window_id_to_frame.items():
            frame.document.zoom.mark()
        self.set_needs_render_all_frames()

    def reset_zoom(self):
        self.zoom = 1
        for id, frame in self.window_id_to_frame.items():
            frame.document.zoom.mark()
        self.set_needs_render_all_frames()

    def run_animation_frame(self, scroll):
        if not self.root_frame.scroll_changed_in_frame:
            self.root_frame.scroll = scroll

        needs_composite = False
        for (window_id, frame) in self.window_id_to_frame.items():
            frame.js.dispatch_RAF(frame.window_id)
    
            for node in tree_to_list(frame.nodes, []):
                for (property_name, animation) in \
                    node.animations.items():
                    value = animation.animate()
                    if value:
                        node.style[property_name].set(value)
                        if wbetools.USE_COMPOSITING and \
                            property_name == "opacity":
                            self.composited_updates.append(node)
                            self.set_needs_paint()
                        else:
                            frame.set_needs_layout()
            if frame.needs_style or frame.needs_layout:
                needs_composite = True

        self.render()

        if self.focus and self.focused_frame.needs_focus_scroll:
            self.focused_frame.scroll_to(self.focus)
            self.focused_frame.needs_focus_scroll = False

        scroll = None
        if self.root_frame.scroll_changed_in_frame:
            scroll = self.root_frame.scroll

        composited_updates = {}
        if not needs_composite:
            for node in self.composited_updates:
                composited_updates[node] = node.save_layer
        self.composited_updates.clear()

        root_frame_focused = not self.focused_frame or \
                self.focused_frame == self.root_frame
        commit_data = CommitData(
            self.root_frame.url, scroll,
            root_frame_focused,
            math.ceil(self.root_frame.document.height.get()),
            self.display_list, composited_updates,
            self.accessibility_tree,
            self.focus
        )
        self.display_list = None
        self.root_frame.scroll_changed_in_frame = False

        self.browser.commit(self, commit_data)

def add_main_args():
    import argparse

    parser = argparse.ArgumentParser(description='Chapter 13 code')
    parser.add_argument("url", type=str, help="URL to load")
    parser.add_argument('--single_threaded', action="store_true", default=False,
        help='Whether to run the browser without a browser thread')
    parser.add_argument('--disable_compositing', action="store_true",
        default=False, help='Whether to composite some elements')
    parser.add_argument('--disable_gpu', action='store_true',
        default=False, help='Whether to disable use of the GPU')
    parser.add_argument('--show_composited_layer_borders', action="store_true",
        default=False, help='Whether to visually indicate composited layer borders')
    parser.add_argument("--force_cross_origin_iframes", action="store_true",
        default=False, help="Whether to treat all iframes as cross-origin")
    parser.add_argument("--assert_layout_clean", action="store_true",
        default=False, help="Assert layout is clean once complete")
    parser.add_argument("--print_invalidation_dependencies", action="store_true",
        default=False, help="Whether to print out all invalidation dependencies")
    args = parser.parse_args()

    wbetools.USE_BROWSER_THREAD = not args.single_threaded
    wbetools.USE_GPU = not args.disable_gpu
    wbetools.USE_COMPOSITING = not args.disable_compositing and not args.disable_gpu
    wbetools.SHOW_COMPOSITED_LAYER_BORDERS = args.show_composited_layer_borders
    wbetools.FORCE_CROSS_ORIGIN_IFRAMES = args.force_cross_origin_iframes
    wbetools.ASSERT_LAYOUT_CLEAN = args.assert_layout_clean
    wbetools.PRINT_INVALIDATION_DEPENDENCIES = \
        args.print_invalidation_dependencies

    return args
    

if __name__ == "__main__":
    args = add_main_args()
    main_func(args)
