"""
This file compiles the code in Web Browser Engineering,
up to and including Chapter 16 (Reusing Previous Computations),
without exercises.
"""

import sys
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
import wbetools

from lab2 import WIDTH, HEIGHT, HSTEP, VSTEP, SCROLL_STEP
from lab4 import print_tree
from lab5 import BLOCK_ELEMENTS
from lab14 import Text, Element
from lab6 import TagSelector, DescendantSelector
from lab6 import tree_to_list, INHERITED_PROPERTIES
from lab8 import INPUT_WIDTH_PX
from lab10 import COOKIE_JAR
from lab11 import FONTS, NAMED_COLORS, get_font, linespace
from lab11 import parse_color, parse_blend_mode
from lab12 import MeasureTime, REFRESH_RATE_SEC, SETTIMEOUT_JS, XHR_ONLOAD_JS
from lab12 import Task, TaskRunner, SingleThreadedTaskRunner
from lab13 import diff_styles, parse_transition, add_parent_pointers
from lab13 import local_to_absolute, absolute_bounds_for_obj, absolute_to_local
from lab13 import NumericAnimation
from lab13 import map_translation, parse_transform
from lab13 import CompositedLayer, paint_visual_effects
from lab13 import PaintCommand, DrawText, DrawCompositedLayer, \
    DrawLine, DrawRRect, DrawRect
from lab13 import VisualEffect, Blend, Transform, DrawOutline
from lab14 import parse_outline, style, \
    paint_outline, dpx, cascade_priority, \
    is_focusable, get_tabindex, speak_text, \
    CSSParser, mainloop, Chrome, PseudoclassSelector, SPEECH_FILE
from lab15 import URL, HTMLParser, AttributeParser, DrawImage, \
    DocumentLayout, BlockLayout, \
    EmbedLayout, InputLayout, LineLayout, TextLayout, ImageLayout, \
    IframeLayout, JSContext, AccessibilityNode, FrameAccessibilityNode, Frame, Tab, \
    CommitData, Browser, BROKEN_IMAGE, font, \
    IFRAME_WIDTH_PX, IFRAME_HEIGHT_PX, parse_image_rendering, DEFAULT_STYLE_SHEET, \
    EVENT_DISPATCH_JS, RUNTIME_JS, POST_MESSAGE_DISPATCH_JS


class ProtectedField:
    def __init__(self, obj, name, parent=None, dependencies=None,
        invalidations=None):
        self.obj = obj
        self.name = name
        self.parent = parent

        self.value = None
        self.dirty = True
        self.invalidations = set()
        self.frozen_dependencies = (dependencies != None)
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

    @wbetools.named_params
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

    @wbetools.js_hide
    def __str__(self):
        if self.dirty:
            return "<dirty>"
        else:
            return str(self.value)

    def __repr__(self):
        return "ProtectedField({}, {})".format(
            self.obj.node if hasattr(self.obj, "node") else self.obj,
            self.name)

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
    if isinstance(children, ProtectedField):
        children = children.get()
    for child in children:
        print_tree(child, indent + 2)

@wbetools.patch(tree_to_list)
def tree_to_list(tree, list):
    list.append(tree)
    children = tree.children
    if isinstance(children, ProtectedField):
        children = children.get()
    for child in children:
        tree_to_list(child, list)
    return list

@wbetools.patch(paint_outline)
def paint_outline(node, cmds, rect, zoom):
    outline = parse_outline(node.style["outline"].get())
    if not outline: return
    thickness, color = outline
    cmds.append(DrawOutline(rect,
        color, dpx(thickness, zoom)))

@wbetools.patch(font)
def font(css_style, zoom, notify):
    weight = css_style['font-weight'].read(notify)
    style = css_style['font-style'].read(notify)
    size = None
    try:
        size = float(css_style['font-size'].read(notify)[:-2]) * 0.75
    except:
        size = 16
    font_size = dpx(size, zoom)
    return get_font(font_size, weight, style)

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
    blend_mode = node.style["mix-blend-mode"].get()
    translation = parse_transform(node.style["transform"].get())

    if node.style["overflow"].get() == "clip":
        border_radius = float(node.style["border-radius"].get()[:-2])
        if not blend_mode:
            blend_mode = "source-over"
        cmds = [Blend(1.0, "source-over", node,
                      cmds + [Blend(1.0, "destination-in", None, [
                          DrawRRect(rect, 0, "white")])])]

    blend_op = Blend(opacity, blend_mode, node, cmds)
    node.blend_op = blend_op
    return [Transform(translation, rect, node, [blend_op])]
    
CSS_PROPERTIES = {
    "font-size": "inherit", "font-weight": "inherit",
    "font-style": "inherit", "color": "inherit",
    "opacity": "1.0", "transition": "",
    "transform": "none", "mix-blend-mode": None,
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
        self.width.set(width - 2 * dpx(HSTEP, zoom))

        if not self.children:
            child = BlockLayout(self.node, self, None, self.frame)
            self.height.set_dependencies([child.height])
        else:
            child = self.children[0]
        self.children = [child]

        self.x.set(dpx(HSTEP, zoom))
        self.y.set(dpx(VSTEP, zoom))

        child.layout()
        self.has_dirty_descendants = False

        self.height.copy(child.height)

        if wbetools.ASSERT_LAYOUT_CLEAN:
            for obj in tree_to_list(self, []):
                assert not obj.layout_needed()

    def paint_effects(self, cmds):
        if self.frame != self.frame.tab.root_frame and self.frame.scroll != 0:
            rect = skia.Rect.MakeLTRB(
                self.x.get(), self.y.get(),
                self.x.get() + self.width.get(), self.y.get() + self.height.get())
            cmds = [Transform((0, - self.frame.scroll), rect, self.node, cmds)]
        return cmds

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
        self.y = ProtectedField(
            self, "y", self.parent, y_dependencies)

        self.children = ProtectedField(self, "children", self.parent, None,
            [])

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
        w = dpx(INPUT_WIDTH_PX, zoom)
        self.add_inline_child(node, w, InputLayout, self.frame)

    def image(self, node):
        zoom = self.zoom.read(notify=self.children)
        if 'width' in node.attributes:
            w = dpx(int(node.attributes['width']), zoom)
        else:
            w = dpx(node.image.width(), zoom)
        self.add_inline_child(node, w, ImageLayout, self.frame)

    def iframe(self, node):
        zoom = self.zoom.read(notify=self.children)
        if 'width' in self.node.attributes:
            w = dpx(int(self.node.attributes['width']), zoom)
        else:
            w = IFRAME_WIDTH_PX + dpx(2, zoom)
        self.add_inline_child(node, w, IframeLayout, self.frame)

    def word(self, node, word):
        zoom = self.zoom.read(notify=self.children)
        node_font = font(node.style, zoom, notify=self.children)
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
            child = child_class(node, word, line, self.previous_word)
        else:
            child = child_class(node, line, self.previous_word, frame)
        line.children.append(child)
        self.previous_word = child
        zoom = self.zoom.read(notify=self.children)
        self.cursor_x += w + font(node.style, zoom, notify=self.children).measureText(' ')

    def self_rect(self):
        return skia.Rect.MakeLTRB(
            self.x.get(), self.y.get(), self.x.get() + self.width.get(),
            self.y.get() + self.height.get())

    def paint(self):
        cmds = []
        bgcolor = self.node.style["background-color"].get()
        if bgcolor != "transparent":
            radius = dpx(
                float(self.node.style["border-radius"].get()[:-2]),
                self.zoom.get())
            cmds.append(DrawRRect(self.self_rect(), radius, bgcolor))
        return cmds
 
    def paint_effects(self, cmds):
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

        cmds = paint_visual_effects(self.node, cmds, self.self_rect())
        return cmds

def DrawCursor(elt, offset):
    x = elt.x.get() + offset
    return DrawLine(x, elt.y.get(), x, elt.y.get() + elt.height.get(), "red", 1)

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
            if isinstance(child, TextLayout):
                new_y += child.ascent.read(notify=child.y) / 1.25
            else:
                new_y += child.ascent.read(notify=child.y)
            child.y.set(new_y)

        max_ascent = self.ascent.read(notify=self.height)
        max_descent = self.descent.read(notify=self.height)

        self.height.set(max_ascent + max_descent)

        self.has_dirty_descendants = False

    def paint_effects(self, cmds):
        outline_rect = skia.Rect.MakeEmpty()
        outline_node = None
        for child in self.children:
            child_outline = parse_outline(child.node.parent.style["outline"].get())
            if child_outline:
                outline_rect.join(child.self_rect())
                outline_node = child.node.parent

        if outline_node:
            paint_outline(outline_node, cmds, outline_rect, self.zoom.get())
        return cmds

@wbetools.patch(TextLayout)
class TextLayout:
    def __init__(self, node, word, parent, previous):
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
        self.font.set(font(self.node.style, zoom, notify=self.font))

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

    def paint(self):
        cmds = []
        leading = self.height.get() / 1.25 * .25 / 2
        color = self.node.style['color'].get()
        cmds.append(DrawText(
            self.x.get(), self.y.get() + leading,
            self.word, self.font.get(), color))
        return cmds

    def self_rect(self):
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
        self.descent = ProtectedField(
            self, "descent", self.parent, [])
        if self.previous:
            x_dependencies = \
                [self.previous.x, self.previous.font,
                self.previous.width]
        else:
            x_dependencies = [self.parent.x]
        self.x = ProtectedField(
            self, "x", self.parent, x_dependencies)
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

    def layout(self):
        self.zoom.copy(self.parent.zoom)

        zoom = self.zoom.read(notify=self.font)
        self.font.set(font(self.node.style, zoom, notify=self.font))

        if self.previous:
            assert hasattr(self, "previous")
            prev_x = self.previous.x.read(notify=self.x)
            prev_font = self.previous.font.read(notify=self.x)
            prev_width = self.previous.width.read(notify=self.x)
            self.x.set(prev_x + prev_font.measureText(' ') + prev_width)
        else:
            self.x.copy(self.parent.x)

        self.has_dirty_descendants = False

@wbetools.patch(InputLayout)
class InputLayout(EmbedLayout):
    def layout(self):
        if not self.layout_needed(): return
        EmbedLayout.layout(self)
        zoom = self.zoom.read(notify=self.width)
        self.width.set(dpx(INPUT_WIDTH_PX, zoom))

        font = self.font.read(notify=self.height)
        self.height.set(linespace(font))

        height = self.height.read(notify=self.ascent)
        self.ascent.set(-height)
        self.descent.set(0)

    def self_rect(self):
        return skia.Rect.MakeLTRB(
            self.x.get(), self.y.get(), self.x.get() + self.width.get(),
            self.y.get() + self.height.get())

    def paint(self):
        cmds = []

        bgcolor = self.node.style["background-color"].get()
        if bgcolor != "transparent":
            radius = dpx(
                float(self.node.style["border-radius"].get()[:-2]),
                self.zoom.get())
            cmds.append(DrawRRect(self.self_rect(), radius, bgcolor))

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

        return cmds

    def paint_effects(self, cmds):
        cmds = paint_visual_effects(self.node, cmds, self.self_rect())
        paint_outline(self.node, cmds, self.self_rect(), self.zoom.get())
        return cmds

@wbetools.patch(ImageLayout)
class ImageLayout(EmbedLayout):
    def layout(self):
        if not self.layout_needed(): return
        EmbedLayout.layout(self)
        width_attr = self.node.attributes.get('width')
        height_attr = self.node.attributes.get('height')
        image_width = self.node.image.width()
        image_height = self.node.image.height()
        aspect_ratio = image_width / image_height

        w_zoom = self.zoom.read(notify=self.width)
        h_zoom = self.zoom.read(notify=self.height)
        if width_attr and height_attr:
            self.width.set(dpx(int(width_attr), w_zoom))
            self.img_height = dpx(int(height_attr), h_zoom)
        elif width_attr:
            self.width.set(dpx(int(width_attr), w_zoom))
            w = self.width.read(notify=self.height)
            self.img_height = w / aspect_ratio
        elif height_attr:
            self.img_height = dpx(int(height_attr), h_zoom)
            self.width.set(self.img_height * aspect_ratio)
        else:
            self.width.set(dpx(image_width, w_zoom))
            self.img_height = dpx(image_height, h_zoom)
        font = self.font.read(notify=self.height)
        self.height.set(max(self.img_height, linespace(font)))
        height = self.height.read(notify=self.ascent)
        self.ascent.set(-height)
        self.descent.set(0)

    def paint(self):
        cmds = []
        rect = skia.Rect.MakeLTRB(
            self.x.get(),
            self.y.get() + self.height.get() - self.img_height,
            self.x.get() + self.width.get(),
            self.y.get() + self.height.get())
        quality = self.node.style["image-rendering"].get()
        cmds.append(DrawImage(self.node.image, rect, quality))
        return cmds

@wbetools.patch(IframeLayout)
class IframeLayout(EmbedLayout):
    def layout(self):
        if not self.layout_needed(): return
        EmbedLayout.layout(self)
        width_attr = self.node.attributes.get('width')
        height_attr = self.node.attributes.get('height')

        w_zoom = self.zoom.read(notify=self.width)
        if width_attr:
            self.width.set(dpx(int(width_attr) + 2, w_zoom))
        else:
            self.width.set(dpx(IFRAME_WIDTH_PX + 2, w_zoom))

        zoom = self.zoom.read(notify=self.height)
        if height_attr:
            self.height.set(dpx(int(height_attr) + 2, zoom))
        else:
            self.height.set(dpx(IFRAME_HEIGHT_PX + 2, zoom)) 

        if self.node.frame and self.node.frame.loaded:
            self.node.frame.frame_height = \
                self.height.get() - dpx(2, self.zoom.get())
            self.node.frame.frame_width = \
                self.width.get() - dpx(2, self.zoom.get())
            self.node.frame.document.width.mark()

        height = self.height.read(notify=self.ascent)
        self.ascent.set(-height)
        self.descent.set(0)

    def paint(self):
        cmds = []
        rect = skia.Rect.MakeLTRB(
            self.x.get(), self.y.get(),
            self.x.get() + self.width.get(),
            self.y.get() + self.height.get())
        bgcolor = self.node.style["background-color"].get()
        if bgcolor != 'transparent':
            radius = dpx(float(
                self.node.style["border-radius"].get()[:-2]),
                self.zoom.get())
            cmds.append(DrawRRect(rect, radius, bgcolor))
        return cmds

    def paint_effects(self, cmds):
        rect = skia.Rect.MakeLTRB(
            self.x.get(), self.y.get(),
            self.x.get() + self.width.get(),
            self.y.get() + self.height.get())
        diff = dpx(1, self.zoom.get())
        offset = (self.x.get() + diff, self.y.get() + diff)
        cmds = [Transform(offset, rect, self.node, cmds)]
        inner_rect = skia.Rect.MakeLTRB(
            self.x.get() + diff, self.y.get() + diff,
            self.x.get() + self.width.get() - diff,
            self.y.get() + self.height.get() - diff)
        internal_cmds = cmds
        internal_cmds.append(
            Blend(1.0, "destination-in", None, [
                          DrawRRect(inner_rect, 0, "white")]))
        cmds = [Blend(1.0, "source-over", self.node, internal_cmds)]
        paint_outline(self.node, cmds, rect, self.zoom.get())
        cmds = paint_visual_effects(self.node, cmds, inner_rect)
        return cmds

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
            for property, (old_value, new_value, num_frames) in \
                transitions.items():
                if property == "opacity":
                    frame.set_needs_render()
                    animation = NumericAnimation(
                        old_value, new_value, num_frames)
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

def paint_tree(layout_object, display_list):
    cmds = layout_object.paint()

    if isinstance(layout_object, IframeLayout) and \
        layout_object.node.frame and \
        layout_object.node.frame.loaded:
        paint_tree(layout_object.node.frame.document, cmds)
    else:
        if isinstance(layout_object.children, ProtectedField):
            for child in layout_object.children.get():
                paint_tree(child, cmds)
        else:
            for child in layout_object.children:
                paint_tree(child, cmds)

    cmds = layout_object.paint_effects(cmds)
    display_list.extend(cmds)

@wbetools.patch(Frame)
class Frame:
    def load(self, url, payload=None):
        self.loaded = False
        self.zoom = 1
        self.scroll = 0
        self.scroll_changed_in_frame = True
        headers, body = url.request(self.url, payload)
        body = body.decode("utf8", "replace")
        self.url = url

        self.allowed_origins = None
        if "content-security-policy" in headers:
           csp = headers["content-security-policy"].split()
           if len(csp) > 0 and csp[0] == "default-src":
               self.allowed_origins = csp[1:]

        self.nodes = HTMLParser(body).parse()

        if self.js: self.js.discarded = True
        self.js = self.tab.get_js(url)
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

            try:
                header, body = script_url.request(url)
            except:
                continue
            body = body.decode("utf8", "replace")
            task = Task(self.js.run, script_url, body,
                self.window_id)
            self.tab.task_runner.schedule_task(task)

        self.rules = DEFAULT_STYLE_SHEET.copy()
        links = [node.attributes["href"]
                 for node in tree_to_list(self.nodes, [])
                 if isinstance(node, Element)
                 and node.tag == "link"
                 and node.attributes.get("rel") == "stylesheet"
                 and "href" in node.attributes]
        for link in links:  
            style_url = url.resolve(link)
            if not self.allowed_request(style_url):
                print("Blocked style", link, "due to CSP")
                continue
            try:
                header, body = style_url.request(url)
            except:
                continue
            self.rules.extend(CSSParser(body.decode("utf8", "replace")).parse())

        images = [node
            for node in tree_to_list(self.nodes, [])
            if isinstance(node, Element)
            and node.tag == "img"]
        for img in images:
            try:
                src = img.attributes.get("src", "")
                image_url = url.resolve(src)
                assert self.allowed_request(image_url), \
                    "Blocked load of " + str(image_url) + " due to CSP"
                header, body = image_url.request(url)
                img.encoded_data = body
                data = skia.Data.MakeWithoutCopy(body)
                img.image = skia.Image.MakeFromEncoded(data)
                assert img.image, \
                    "Failed to recognize image format for " + str(image_url)
            except Exception as e:
                print("Image", img.attributes.get("src", ""),
                    "crashed", e)
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
            task = Task(iframe.frame.load, document_url)
            self.tab.task_runner.schedule_task(task)

        self.document = DocumentLayout(self.nodes, self)
        self.set_needs_render()
        self.loaded = True

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
            self.tab.needs_accessibility = True
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
        self.set_needs_paint()

    def clamp_scroll(self, scroll):
        height = math.ceil(self.document.height.get() + 2*VSTEP)
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
                abs_bounds = \
                    absolute_bounds_for_obj(elt.layout_object)
                border = dpx(1, elt.layout_object.zoom.get())
                new_x = x - abs_bounds.left() - border
                new_y = y - abs_bounds.top() - border
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
            self.scroll *= 1.1
        else:
            self.zoom *= 1 / 1.1
            self.scroll *= 1 / 1.1
        for id, frame in self.window_id_to_frame.items():
            frame.document.zoom.mark()
        self.scroll_changed_in_tab = True
        self.set_needs_render_all_frames()

    def reset_zoom(self):
        self.scroll /= self.zoom
        self.zoom = 1
        for id, frame in self.window_id_to_frame.items():
            frame.document.zoom.mark()
        self.scroll_changed_in_tab = True
        self.set_needs_render_all_frames()

    def run_animation_frame(self, scroll):
        if not self.root_frame.scroll_changed_in_frame:
            self.root_frame.scroll = scroll

        needs_composite = False
        for (window_id, frame) in self.window_id_to_frame.items():
            if not frame.loaded:
                continue

            self.browser.measure.time('script-runRAFHandlers')
            frame.js.dispatch_RAF(frame.window_id)
            self.browser.measure.stop('script-runRAFHandlers')
    
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

        for (window_id, frame) in self.window_id_to_frame.items():
            if frame == self.root_frame: continue
            if frame.scroll_changed_in_frame:
                needs_composite = True
                frame.scroll_changed_in_frame = False

        scroll = None
        if self.root_frame.scroll_changed_in_frame:
            scroll = self.root_frame.scroll

        composited_updates = None
        if not needs_composite:
            composited_updates = {}
            for node in self.composited_updates:
                composited_updates[node] = node.blend_op
        self.composited_updates = []

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

    def render(self):
        self.browser.measure.time('render')

        for id, frame in self.window_id_to_frame.items():
            if frame.loaded:
                frame.render()

        if self.needs_accessibility:
            self.accessibility_tree = AccessibilityNode(self.root_frame.nodes)
            self.accessibility_tree.build()
            self.needs_accessibility = False
            self.needs_paint = True

        if self.needs_paint:
            self.display_list = []
            self.browser.measure.time('paint')
            paint_tree(self.root_frame.document, self.display_list)
            self.browser.measure.stop('paint')
            self.needs_paint = False

        self.browser.measure.stop('render')

@wbetools.patch(AccessibilityNode)
class AccessibilityNode:
    def compute_bounds(self):
        if self.node.layout_object:
            return [absolute_bounds_for_obj(self.node.layout_object)]
        if isinstance(self.node, Text):
            return []
        inline = self.node.parent
        bounds = []
        while not inline.layout_object: inline = inline.parent
        for line in inline.layout_object.children.get():
            line_bounds = skia.Rect.MakeEmpty()
            for child in line.children:
                if child.node.parent == self.node:
                    line_bounds.join(skia.Rect.MakeXYWH(
                        child.x.get(), child.y.get(), child.width.get(), child.height.get()))
            bounds.append(line_bounds)
        return bounds

if __name__ == "__main__":
    wbetools.parse_flags()
    sdl2.SDL_Init(sdl2.SDL_INIT_EVENTS)
    browser = Browser()
    browser.new_tab(URL(sys.argv[1]))
    browser.draw()
    mainloop(browser)
