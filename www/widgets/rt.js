/* This file simulates Python packages used by the WBE browser */

export {
    breakpoint, filesystem, ctypes, math,
    socket, ssl, sys, tkinter, dukpy, urllib, html, random, wbetools,
    truthy, comparator, pysplit, pyrsplit, asyncfilter,
    rt_constants, Widget, http_textarea, skia, sdl2, init_skia,
    init_window, threading, time, OpenGL, patch_class, patch_function, dict,
    gtts, os, playsound
    };

function patch_class(cls, patched_cls) {
    for (let val of Object.getOwnPropertyNames(patched_cls.prototype)) {
        cls.prototype[val] = patched_cls.prototype[val]
    }
}

function patch_function(f, patched_f) {
    f = patched_f
}

function wrap_class(cls, fn) {
    var f = function(...args) {
        return new cls(...args);
    }
    if (fn) fn(f);
    return f;
}

class Dict {
    async get(key) {
        return this[key];
    }
}

function dict(args) {
    let d = new Dict();
    args.forEach((arg) => {
        d[arg[0]] = arg[1]
    });
    return d;
}

function http_ok(body, headers) {
    let text = "HTTP/1.0 200 OK\r\n";
    for (let [k, v] of Object.entries(headers || {})) {
        text += k + ": " + v + "\r\n";
    }
    return text + "\r\n" + body
}

function http_textarea(elt) {
    return function() {
        return http_ok(elt.value);
    }
}

const rt_constants = {};
rt_constants.ZOOM = 1.0;
rt_constants.ROOT_CANVAS = null;
rt_constants.URLS = {};
rt_constants.WINDOW = null;

let fontManager;
let CanvasKit;
let robotoData

class ExpectedError extends Error {
    constructor(msg) {
        super(msg);
    }
}

class WidgetXHRError extends ExpectedError {
    constructor(hostname) {
        super("This widget cannot access " + hostname + " due to sandboxing, " +
              "but the book's Python code should work correctly.");
        this.name = "WidgetXHRError";
    }
}

class socket {
    static AF_INET = "inet";
    static SOCK_STREAM = "stream";
    static IPPROTO_TCP = "tcp";

    static socket = wrap_class(class socket {
        constructor(params) {
            console.assert(params.family == "inet", "socket family must be inet")
            console.assert(params.type == "stream", "socket type must be stream")
            console.assert(params.proto == "tcp", "socket proto must be tcp")
        }

        connect(pair) {
            let [host, port] = pair
            this.host = host
            this.port = port;
            this.input = "";
            this.closed = true;
            this.scheme = "http";
        }

        send(text) {
            this.input += text;
        }

        async makefile(mode, params) {
            if (mode == "r") {
                console.assert(params.encoding == "utf8" && params.newline == "\r\n", "Unknown socket encoding or line ending");
            } else if (mode == "b") {
                // ok
            } else {
                console.assert(false, "Unknown socket makefile mode");
            }
            if (this.is_proxy_socket) return this;

            let [line1] = this.input.split("\r\n", 1);
            let [method, path, protocol] = line1.split(" ");
            this.url = this.scheme + "://" + this.host + path;
            if (this.host == "localhost" && rt_constants.URLS["local://" + this.port]) {
                let s = new socket({family: "inet", type: "stream", proto: "tcp"});
                s.is_proxy_socket = true;
                s.output = this.input;
                await rt_constants.URLS["local://" + this.port](s)
                this.output = s.input;
                this.closed = false;
            } else if (rt_constants.URLS[this.url]) {
                var response = rt_constants.URLS[this.url];
                this.output = typeof response === "function" ? response() : response;
                this.idx = 0;
                this.closed = false;
            } else if (this.host == "browser.engineering") {
                let response = await fetch(path);
                this.output = "HTTP/1.0 " + response.status + " " + response.statusText + "\r\n";
                for (let [header, value] of response.headers.entries()) {
                    if (header.toLowerCase() == "transfer-encoding") continue;
                    if (header.toLowerCase() == "content-encoding") continue;
                    this.output += header + ": " + value + "\r\n";
                }
                this.output += "\r\n";
                this.output += await response.text();
                this.closed = false;
                this.idx = 0;
                return this;
            } else {
                this.output = "HTTP/1.0 " + 404 + "\r\n";
                this.output += "\r\n";
                this.closed = false;
                this.idx = 0;                
            }
            return this;
        }

        readline() {
            console.assert(!this.closed, "Attempt to read from a closed socket")
            let nl = this.output.indexOf("\r\n", this.idx);
            if (nl === -1) nl = this.output.length - 2;
            let line = this.output.substring(this.idx, nl + 2);
            this.idx = nl + 2;
            return line;
        }
        read() {
            console.assert(!this.closed, "Attempt to read from a closed socket")
            let rest = this.output.substring(this.idx);
            this.idx = this.output.length;
            return rest;
        }
        close() {
            this.closed = true;
        }
    })
    
    static accept(port, fn) {
        rt_constants.URLS["local://" + port] = fn;
    }
}

class ssl {
    static create_default_context = wrap_class(class {
        wrap_socket(s, params) {
            console.assert(s.host == params.server_hostname, "Invalid SSL server name, does not match socket host");
            s.scheme = "https";
            return s;
        }
    })
}

class sys {
}

class tkinter { 
    static Tk = function(...args) {
        if (rt_constants.WINDOW) {
            return rt_constants.WINDOW;
        }

        return wrap_class(class {
            constructor() {
                this.elt = rt_constants.ROOT_CANVAS;
                this.bindings = {}
                this.event_names_to_key = {}
                rt_constants.WINDOW = this;
            }

            bind(key, callback) {
                let event_name, fn;

                if (['<Up>', '<Down>', '<Left>', '<Right>'].indexOf(key) !== -1) {
                    event_name = "keydown";
                    fn = function(e) {
                        if (e.key == 'Arrow' + key.substr(1, key.length-2)) {
                            e.preventDefault();
                            callback({}).catch(on_error);
                        }
                    };
                } else if (key == '<Return>') {
                    event_name = "keydown";
                    fn = function(e) {
                        if (e.key == 'Enter') {
                            e.preventDefault();
                            callback({}).catch(on_error);
                        }
                    };
                } else if (['<Button-1>', '<Button-2>', '<Button-3>'].indexOf(key) !== -1) {
                    event_name = "mousedown";
                    fn = function(e) {
                        if (e.button == key.substr(8, 1) - 1) {
                            callback({ x: e.offsetX, y: e.offsetY }).catch(on_error);
                        }
                    };
                } else if (key == '<Configure>') {
                    event_name = "resize";
                    fn = function(e) {
                        callback({}).catch(on_error);
                    };
                } else if (key == '<Key>') {
                    event_name = "keydown";
                    fn = function(e) {
                        if (e.key.length == 1) {
                            e.preventDefault();
                            callback({ char: e.key }).catch(on_error);
                        };
                    };
                } else if (key.length == 1) {
                    event_name = "keydown";
                    fn = function(e) {
                        if (e.key == key) {
                            e.preventDefault();
                            callback({ char: e.key }).catch(on_error);
                        }
                    };
                } else {
                    console.error("Trying to bind unsupported event", key);
                }
                if (key in this.bindings) {
                    this.bindings[key] = fn;
                    return;
                }
                this.bindings[key] = fn;
                if (!(event_name in this.event_names_to_key)) {
                    this.event_names_to_key[event_name] = []

                    window.addEventListener(event_name, function(e) {
                        let arr = this.event_names_to_key[event_name];
                        for (let index in arr) {
                            this.bindings[arr[index]](e);
                        }
                    }.bind(this));
                }

                this.event_names_to_key[event_name].push(key)
            }
        })(...args);
    }

    static Canvas = wrap_class(class {
        constructor(tk, params) {
            this.tk = tk;
            this.tk.elt.width = params.width * rt_constants.ZOOM;
            this.tk.elt.height = params.height * rt_constants.ZOOM;
            this.ctx = tk.elt.getContext('2d');
            this.ctx.font = "normal normal " + 16 * rt_constants.ZOOM + "px Merriweather"
        }

        pack() {}

        delete(who) {
            console.assert(who === "all", "tkinter.Canvas.delete expects argument 'all'");
            this.ctx.clearRect(0, 0, this.tk.elt.width, this.tk.elt.height);
        }

        create_rectangle(x1, y1, x2, y2, params) {
            this.ctx.beginPath();
            this.ctx.rect(x1 * rt_constants.ZOOM, y1 * rt_constants.ZOOM, (x2 - x1) * rt_constants.ZOOM, (y2 - y1) * rt_constants.ZOOM);
            this.ctx.fillStyle = params.fill ?? "transparent";
            this.ctx.fill();
            if ((params.width ?? 0) != 0) {
                this.ctx.lineWidth = params.width;
                this.ctx.strokeStyle = "black";
                this.ctx.stroke()
            }
        }

        create_line(x1, y1, x2, y2) {
            this.ctx.beginPath();
            this.ctx.moveTo(x1 * rt_constants.ZOOM, y1 * rt_constants.ZOOM);
            this.ctx.lineTo(x2 * rt_constants.ZOOM, y2 * rt_constants.ZOOM);
            this.ctx.lineWidth = 1;
            this.ctx.strokeStyle = "black";
            this.ctx.stroke();
        }

        create_polygon(... args) {
            this.ctx.beginPath();
            this.ctx.moveTo(args[0] * rt_constants.ZOOM, args[1] * rt_constants.ZOOM);
            let i;
            for (i = 2; i < args.length - 1; i += 2) {
                this.ctx.lineTo(args[i] * rt_constants.ZOOM, args[i + 1] * rt_constants.ZOOM);
            }
            this.ctx.fillStyle = args[i].fill ?? "transparent";
            this.ctx.fill();
            this.ctx.strokeWidth = 1;
            this.ctx.stroke();
        }

        create_text(x, y, params) {
            if (params.anchor == "nw") {
                this.ctx.textAlign = "left";
                this.ctx.textBaseline = "top";
            } else {
                this.ctx.textAlign = "center";
                this.ctx.textBaseline = "middle";
            }
            if (params.font) this.ctx.font = params.font.string;
            this.ctx.lineWidth = 0;
            this.ctx.fillStyle = params.fill ?? "black";
            if (params.text) this.ctx.fillText(params.text, x * rt_constants.ZOOM, y * rt_constants.ZOOM);
        }
    })
    
    static font = {
        Font: wrap_class(class {
            constructor(params) {
                this.size = params.size ?? 16;
                this.weight = params.weight ?? "normal";
                this.style = params.style ?? "normal";
                this.string = (this.style == "roman" ? "normal" : this.style) + 
                    " " + this.weight + " " + this.size * rt_constants.ZOOM + "px Merriweather";

                this.$metrics = null;
            }

            measure(text) {
                let ctx = rt_constants.ROOT_CANVAS.getContext('2d');
                ctx.font = this.string;
                return ctx.measureText(text).width / rt_constants.ZOOM;
            }

            metrics(field) {
                if (!this.$metrics) {
                    let ctx = rt_constants.ROOT_CANVAS.getContext('2d');
                    ctx.textBaseline = "alphabetic";
                    ctx.font = this.string;
                    let m = ctx.measureText("Hxy");

                    let asc = ctx.measureText("Hxy").fontBoundingBoxAscent / rt_constants.ZOOM;
                    let desc = ctx.measureText("Hxy").fontBoundingBoxDescent / rt_constants.ZOOM;
                    this.$metrics = { ascent: asc, descent: desc, linespace: asc + desc, fixed: 0 };
                }
                if (field) return this.$metrics[field]
                else return this.$metrics;
            }
        })
    }

    static Label = function(font) {}
}

function init_window(browser) {
    let w = tkinter.Tk();
    w.bind("<Down>", (e) => browser.handle_down(e));
    w.bind("<Button-1>", (e) => browser.handle_click(e));
    w.bind("<Key>", (e) => browser.handle_key(e.char));
    w.bind("<Return>", (e) => browser.handle_enter(e));
}

class urllib {
    static parse = class {
        static quote(s) {
            return encodeURIComponent(s);
        }
        static unquote_plus(s) {
            return decodeURIComponent(s);
        }
    }
}

class html {
    static escape(s) {
        // To HTML-escape a string, insert a text node with that
        // contents into the DOM, and read back its HTML. In effect,
        // we're leveraging the browser's unparser to escape text.
        let e = document.createElement("div");
        let t = document.createTextNode(s);
        e.appendChild(t);
        document.documentElement.appendChild(e);
        let html = e.innerHTML;
        e.remove();
        return html;
    }
}

class random {
    static random() {
        return Math.random();
    }
}

class math {
    static ceil(num) {
        return Math.ceil(num);
    }
}

class JSInterpreterError extends ExpectedError {
    constructor() {
        super("This widget cannot execute JavaScript due to sandboxing, " +
             "but the book's Python code should work correctly.");
        this.name = "JSEnvironmentError."
    }
}

class JSExecutionError extends ExpectedError {
    constructor(fn) {
        super("This widget can't handle the " + fn + " exported function's return value, " +
              "but the book's Python code should work correctly.");
        this.name = "JSExecutionError";
    }
}

class dukpy {
    static JSRuntimeError = class {
        constructor(msg) {
            this.msg = msg;
        }
    }
    
    static JSInterpreter = wrap_class(class {
        constructor() {

            if (!crossOriginIsolated) {
                throw new JSInterpreterError(this.host);               
            }

            this.function_table = {};
            this.worker = new Worker("/widgets/dukpy.js");
            this.worker.onmessage = this.onmessage.bind(this);
            this.buffer = new SharedArrayBuffer(1024);
            this.write_buffer = new Int32Array(this.buffer, 4);
            this.flag_buffer = new Int32Array(this.buffer, 0, 1);
            this.promise_stack = [];
            this.worker.postMessage({
                "type": "array",
                "buffer": this.buffer,
            });
        }

        export_function(name, fn) {
            this.function_table[name] = fn;
        }

        evaljs(code, replacements) {
            return new Promise((resolve, reject) => {
                this.promise_stack.push(resolve);
                this.worker.postMessage({
                    "type": "eval",
                    "body": code,
                    "bindings": replacements,
                });
            });
        }
        
        async onmessage(e) {
            switch (e.data.type) {
            case "call":
                let res = await this.function_table[e.data.fn].call(window, ... e.data.args);
                let json_result = JSON.stringify(res);
                let bytes = new TextEncoder().encode(json_result);
                if (bytes.length <= this.write_buffer.length) {
                    for (let i = 0; i < bytes.length; i++) {
                        Atomics.store(this.write_buffer, i, bytes[i]);
                    }
                    Atomics.store(this.flag_buffer, 0, bytes.length);
                    Atomics.notify(this.flag_buffer, 0);
                } else {
                    throw new JSExecutionError(e.data.fn);
                }
                break;

            case "return":
                this.promise_stack.pop()(e.data.data);
                break;
            }
        }
    })
}

class sdl2 {
    static SDL_CreateWindow(name, option1, option2, width, height, shown) {
        return {};
    }

    static SDL_CreateRGBSurfaceFrom(bytes, width, height, depth, pitch,
        red, green, blue, alpha) {
        return {};
    }

    static SDL_Rect(top, left, width, height) {
        return {};
    }

    static SDL_BlitSurface(sdl_surface, sdl_rect, window_surface, window_rect) {
    }

    static SDL_GetWindowSurface(window) {
    }

    static SDL_UpdateWindowSurface(window) {
    }

    static SDL_DestroyWindow(window) {
    }

    static SDL_WINDOWPOS_CENTERED = 0;
    static SDL_WINDOWPOS_CENTERED = 0;
    static SDL_WINDOW_SHOWN = 0;
    static SDL_WINDOW_OPENGL = 0;
    static SDL_BYTEORDER = 0;
    static SDL_BIG_ENDIAN = 0;
}

function patch_canvas(canvas) {
    var oldDrawPath = canvas.drawPath;
    var oldDrawRect = canvas.drawRect;
    var oldDrawRRect = canvas.drawRRect;
    var oldSaveLayer = canvas.saveLayer;
    var oldClipRect = canvas.clipRRect;
    var oldClipRRect = canvas.clipRRect;
    var oldDrawImageRect = canvas.drawImageRect;

    canvas.drawPath = (path, paint) => {
        oldDrawPath.call(canvas, path, paint.getPaint());
    };

    canvas.drawRect = (rect, paint) => {
        oldDrawRect.call(canvas, rect, paint.getPaint());
    };

    canvas.drawRRect = (rrect, paint) => {
        oldDrawRect.call(canvas, rrect, paint.getPaint());
    };

    canvas.drawString = (text, x, y, font, paint) => {
        canvas.drawText(text, x, y, paint.getPaint(), font.getFont())       
    };

    canvas.saveLayer = (paint) => {
        oldSaveLayer.call(canvas, paint.getPaint());
    };

    canvas.clipRect = (rect) => {
        oldClipRect.call(canvas, rect, CanvasKit.ClipOp.Intersect, false);
    };

    canvas.clipRRect = (rect) => {
        oldClipRRect.call(canvas, rect, CanvasKit.ClipOp.Intersect, false);
    };

    canvas.drawImageRect = (image, rect, paint) => {
        oldDrawImageRect.call(canvas, image, rect, paint);
    };
}

class skia {
    static Color = function(red, green, blue, alpha) {
        return CanvasKit.Color(red, green, blue, alpha);
    };

    static Surface = wrap_class(class {
        constructor(width, height, is_root=false) {
            if (is_root) {
                let image_info = width
                rt_constants.ROOT_CANVAS.width =
                    image_info.width * rt_constants.ZOOM;
                rt_constants.ROOT_CANVAS.height =
                    image_info.height * rt_constants.ZOOM;
               this.surface = CanvasKit.MakeCanvasSurface('canvas');
            } else {
                this.surface = CanvasKit.MakeSurface(width, height);
            }
            this.canvas = this.surface.getCanvas();
            patch_canvas(this.canvas);
        }

        getCanvas() {
            return this.canvas;
        }

        makeImageSnapshot() {
            return {tobytes: () => this.surface.flush()}
        }

        draw(canvas, left, top) {
            canvas.drawImage(this.surface.makeImageSnapshot(), left, top,
                new CanvasKit.Paint());
        }

        width() {
            return this.surface.width();
        }

        height() {
            return this.surface.height();
        }
    }, (obj) => {
        obj.MakeRaster = (image_info) => {
            return obj(image_info, undefined, true);
        }
    });

    static ImageInfo = wrap_class(class {
        constructor(width, height) {
            this.width = width
            this.height = height            
        }
    }, (obj) => {
        obj.Make = (width, height, ct, at) => {
            return obj(width, height);
        }
    });

    static Image = {
        open: (image_file) => {
            // TODO
        },
        MakeFromEncoded: (data) => {
            return CanvasKit.MakeImageFromEncoded(data);
        }
    };

    static Data = {
        MakeWithoutCopy: (body) => {
            return body;
        }
    }

    static Rect = {
        fill_in: (rect) => {
            rect.left = () => rect[0];
            rect.top = () => rect[1];
            rect.right = () => rect[2];
            rect.bottom = () => rect[3];
            rect.isEmpty = () => {
                return rect.left() == rect.right() &&
                    rect.top() == rect.bottom();
            };
            rect.join = (other_rect) => {
                rect[0] = Math.min(rect.left(), other_rect.left());
                rect[1] = Math.min(rect.top(), other_rect.top());
                rect[2] = Math.max(rect.right(), other_rect.right());
                rect[3] = Math.max(rect.bottom(), other_rect.bottom());
            };
            rect.intersect = (other_rect) => {
                rect[0] = Math.max(rect.left(), other_rect.left());
                rect[1] = Math.max(rect.top(), other_rect.top());
                rect[2] = Math.min(rect.right(), other_rect.right());
                rect[3] = Math.min(rect.bottom(), other_rect.bottom());
                if (rect[0] > rect[2] || rect[1] > rect[3]) {
                    rect[0] = rect[1] = rect[2] = rect[3] = 0;
                }
            };
            rect.roundOut = () => {
                return skia.Rect.MakeLTRB(
                    Math.floor(rect.left()),
                    Math.floor(rect.top()),
                    Math.ceil(rect.right()),
                    Math.ceil(rect.bottom()));
            };
            rect.width = () => {
                return rect.right() - rect.left();
            };
            rect.height = () => {
                return rect.bottom() - rect.top();
            };
            rect.intersects = (other_rect) => {
                if (rect.top() > other_rect.bottom() ||
                    rect.bottom() < other_rect.top())
                    return false;
                if (rect.left() > other_rect.right() ||
                    other_rect.left() > rect.right())
                    return false;
                return true;
            };
            rect.outset = (x, y) => {
                return skia.Rect.MakeLTRB(
                    rect.left() - 1,
                    rect.top() - 1,
                    rect.right() + 1,
                    rect.bottom() + 1);
            };
            rect.makeOffset = (x, y) => {
                return skia.Rect.MakeLTRB(
                    rect.left() + x,
                    rect.top() + y,
                    rect.right() + x,
                    rect.bottom() + y);
            };
            rect.offset = (x, y) => {
                rect = rect.makeOffset(x, y);
            };
            rect.contains = (x, y) => {
                let other = skia.Rect.MakeXYWH(x, y, 1, 1);
                return rect.intersects(other);
            };
        },

        MakeLTRB: (left, top, right, bottom) => {
            let rect = CanvasKit.LTRBRect(left, top, right, bottom);
            skia.Rect.fill_in(rect, left, top, right, bottom);
            return rect;
        },
        MakeXYWH: (x, y, width, height) => {
            let rect = CanvasKit.XYWHRect(x, y, width, height);
            skia.Rect.fill_in(rect, x, y, x + width, y + height);
            return rect;
        },
        MakeEmpty: () => {
            let rect = CanvasKit.XYWHRect(0, 0, 0, 0);
            skia.Rect.fill_in(rect, 0, 0, 0, 0);
            return rect;
        }
    };

    static RRect = {
        MakeRectXY : (rect, x, y) => {
            return CanvasKit.RRectXY(rect, x, y);
        }
    };

    static Paint;

    static RRect = {
        MakeRectXY: function(rect, x, y) {
            return CanvasKit.RRectXY(rect, x, y);
        }
    };

    static Path;

    static Font;

    static ColorWHITE;
    static colorRED;
    static colorGREEN;
    static colorBLUE;
    static colorGRAY;
    static colorBLACK;

    static FontStyle;

    static Typeface = function (font_name, style_info) {
        return null;
    }

    static BlendMode;

    static ColorSetARGB = function(r, g, b, a) {
        return CanvasKit.Color(r, g, b, a);
    }

    static Matrix = wrap_class(class {
        setTranslate(x, y)  {
            this.x = x;
            this.y = y;
        }

        mapRect(rect) {
            return skia.Rect.LTRBRect(
                rect.left() + x, rect.top() + y, rect.right() + x,
                rect.bottom() + y);
        }
    });
}

function init_skia(canvasKit, robotoData) {
    CanvasKit = canvasKit;
    robotoData = robotoData;
    fontManager = CanvasKit.FontMgr.FromData([robotoData]);

    skia.Paint = wrap_class(class {
        constructor(args) {
            this.paint = new CanvasKit.Paint();
            if (!args)
                return;
            for (const [key, value] of Object.entries(args)) {
                switch (key) {
                    case "Color":
                        this.paint.setColor(value);
                        continue;
                    case "AntiAlias":
                        this.paint.setAntiAlias(value);
                        continue;
                    case "BlendMode":
                        this.paint.setBlendMode(value);
                        continue;
                    case "Alphaf":
                        this.paint.setAlphaf(value);
                        continue;
                    case "Style":
                        this.paint.setStyle(value);
                        continue;
                    case "StrokeWidth":
                        this.paint.setStrokeWidth(value);
                        continue;
                    default:
                        throw "Unknown Skia Paint value: " + key;
                }
            }
        }

        getPaint() {
            return this.paint;
        }
    }, (obj) => {
        obj.kStroke_Style = CanvasKit.PaintStyle.Stroke;
        obj.kFill_Style = CanvasKit.PaintStyle.Fill;
    });

    skia.Path = wrap_class(CanvasKit.Path);

    skia.Font = wrap_class(class {
        constructor(ignored_typeface, size) {
            this.font = new CanvasKit.Font(
                fontManager.matchFamilyStyle(
                    fontManager.getFamilyName(0), {}));
            this.font.setSize(size / 1.333);
        }

        getFont() {
            return this.font;
        }

        getMetrics() {
            return {
                fAscent: -this.font.getSize(),
                fDescent: this.font.getSize() * 0.3
            };
        }

        measureText(t) {
            let glyphIds = this.font.getGlyphIDs(t);
            let glyphWidths = this.font.getGlyphWidths(glyphIds);
            let sum = 0;
            for (let i = 0; i < glyphWidths.length; i++) {
                sum += glyphWidths[i];
            }
            return sum;
        }
    });

    skia.ColorWHITE = CanvasKit.WHITE;
    skia.ColorRED = CanvasKit.RED;
    skia.ColorGREEN = CanvasKit.GREEN;
    skia.ColorBLUE = CanvasKit.BLUE;
    skia.ColorGRAY = CanvasKit.Color(0x80, 0x80, 0x80, 0xFF);
    skia.ColorBLACK = CanvasKit.BLACK;

    skia.BlendMode = {
        kSrcOver: CanvasKit.BlendMode.SrcOver,
        kMultiply: CanvasKit.BlendMode.Multiply,
        kDifference: CanvasKit.BlendMode.Multiply,
        kDstIn: CanvasKit.BlendMode.Difference
    }
    skia.FontStyle = wrap_class(class {
        constructor(weight, width, style) {}
    }, (f) => {
        f.kBold_Weight = CanvasKit.FontWeight.Bold,
        f.kNormal_Weight = CanvasKit.FontWeight.Normal,
        f.kItalic_Slant = CanvasKit.FontSlant.Italic,
        f.kUpright_Slant = CanvasKit.FontSlant.Upright
    });
}

class OpenGL {
    static GL = {
        GL_RGBA8 : 0
    }
}

class gtts {
    static gTTS(text) {
        return { save: (file) => {} }
    }
}

class playsound {
    static playsound(file) {
    }
}

class os {
    static remove(file) {
    }
}

class ctypes {
}

class wbetools {
    static USE_BROWSER_THREAD = false;
}

class Breakpoint {
    constructor() {
        this.handlers = {};
    }

    async event(name, ...args) {
        for (let h of this.handlers[name] ?? []) {
            await h(...args);
        }
    }

    capture(name, fn) {
        if (!this.handlers.hasOwnProperty(name)) this.handlers[name] = [];
        this.handlers[name].push(fn);
    }
}

const breakpoint = new Breakpoint();

let on_error = function(e) { throw e; }

class Widget {
    constructor(elt) {
        this.elt = elt;
        if (elt) {
            this.controls = {
                reset: elt.querySelector(".reset"),
                back: elt.querySelector(".stepb"),
                next: elt.querySelector(".stepf"),
                animate: elt.querySelector(".play"),
                input: elt.querySelector("#input-controls"),
            };
            if (this.controls.reset) this.controls.reset.addEventListener("click", this.reset.bind(this));
            if (this.controls.back) this.controls.back.addEventListener("click", this.back.bind(this));
            if (this.controls.next) this.controls.next.addEventListener("click", this.next.bind(this));
            if (this.controls.animate) this.controls.animate.addEventListener("click", this.animate.bind(this));
        } else {
            this.controls = {};
        }
        window.addEventListener("resize", this.redraw.bind(this));

        this.step = -1;
        this.stop = -1;
        this.k = null;
        this.runner = null;
        this.timer = null;

        on_error = this.on_error;
    }
    
    on_error(e) {
        if (e instanceof ExpectedError) {
            console.log(e);
        } else {
            throw e;
        }
    }

    pause(evt, cb) {
        let that = this;
        breakpoint.capture(evt, function(...args) {
            return new Promise(function (resolve) {
                that.step += 1;
                that.controls.back.disabled = (that.step <= 0);
                if (cb) cb(...args);
                if (that.step < that.stop && that.stop >= 0) {
                    resolve();
                } else {
                    that.k = resolve;
                    that.stop = -1;
                }
            });
        });
        return this;
    }

    listen(evt, cb) {
        console.assert(cb, "Widget.listen() requires a callback");
        breakpoint.capture(evt, function(...args) {
            return new Promise(function (resolve) {
                if (cb) cb(...args); resolve();
            });
        });
        return this;
    }

    reset(e) {
        if (this.elt)
            this.elt.classList.remove("running");
        this.step = -1;
        this.k = this.runner;
        if (this.timer) clearInterval(this.timer);
        this.timer = null;
        if (this.controls.reset) this.controls.reset.disabled = true;
        if (this.controls.back) this.controls.back.disabled = true;
        if (this.controls.input) this.controls.input.disabled = false;
        if (this.controls.next) this.controls.next.disabled = false;
        if (this.controls.animate) this.controls.animate.disabled = false;
        if (this.controls.next) this.controls.next.children[0].textContent = "Start";
        if (e) e.preventDefault();
    }

    back(e) {
        this.stop = this.step - 1;
        this.reset();
        this.next();
        if (e) e.preventDefault();
    }

    redraw(e) {
        this.stop = this.step;
        this.reset();
        this.next();
    }

    next(e) {
        if (this.elt)
            this.elt.classList.add("running");
        console.assert(this.k, "Tried to step forward but no next state available");
        if (this.controls.next) this.controls.next.children[0].textContent = "Next";
        if (this.controls.input) this.controls.input.disabled = true;
        if (this.controls.reset) this.controls.reset.disabled = false;
        if (this.controls.back) this.controls.back.disabled = false;
        this.k();
        if (e) e.preventDefault();
    }

    animate(e) {
        this.timer = setInterval(this.next.bind(this), 250);
        this.next();
        if (e) e.preventDefault();
    }

  
    end() {
        this.k = null;
        this.stop = -1;
        if (this.timer) clearInterval(this.timer);
        this.timer = null;
        if (this.controls.next) this.controls.next.disabled = true;
        if (this.controls.animate) this.controls.animate.disabled = true;
    }

    run(k) {
        let that = this;
        this.runner = async function() {
            try {
                await k();
            } catch (e) {
                on_error(e);
            } finally {
                that.end();
            }
        }
        this.reset();
        return this;
    }
}

function truthy(x) {
    // Emulates Python's truthiness function
    if (Array.isArray(x)) {
        return x.length > 0;
    } else if (typeof x === "number") {
        return x != 0;
    } else if (typeof x === "string") {
        return x.length > 0;
    } else if (typeof x === "boolean") {
        return x;
    } else if (typeof x === "undefined" || x === null) {
        return false;
    } else if (typeof x === "object") {
        return Object.entries(x).length > 0;
    } else {
        console.error("Checking truthiness of weird value", x);
        return true;
    }
}

function pysplit(x, sep, cnt) {
    let parts = x.split(sep)
    return parts.slice(0, cnt).concat([parts.slice(cnt).join(sep)])
}

function pyrsplit(x, sep, cnt) {
    let parts = x.split(sep)
    return [parts.slice(0, -cnt).join(sep)].concat(parts.slice(-cnt))
}

function comparator(f) {
    return function(a, b) {
        let fa = f(a), fb = f(b);
        if (fa < fb) return -1;
        else if (fb < fa) return 1;
        else return 0;
    }
}

async function asyncfilter(fn, arr) {
    let out = [];
    for (var i = 0; i < arr.length; i++) {
        if (await fn(arr[i])) {
            out.push(arr[i]);
        }
    }
    return out;
}

class File {
    constructor(contents) {
        this.contents = contents;
        this.writable = false;
    }
    read() {
        return this.contents;
    }
    write(s) {
        if (! this.writable)
            throw "File is not writable"
        this.contents += s;
    }
    close() {}
}

class FileSystem {
    constructor() {
        this.files = {};
    }
    register(name, contents) {
        this.files[name] = contents;
    }
    open(name, mode="r") {
        if (mode === "r") {
            return new File(this.files[name]);
        } else {
            let f = new File("");
            f.writable = true;
            return f;
        }
    }
}

const filesystem = new FileSystem();

class threading {
    static Timer = wrap_class(class {
        constructor(refresh_rate_sec, callback) {
            this.refresh_rate_ms = refresh_rate_sec * 1000;
            this.callback = callback;
        }

        start() {
            setTimeout(this.callbac, this.refresh_rate_ms)
        }
    });

    static Thread = wrap_class(class {
        constructor(target) {
        }

        start() {

        }
    });

    static Condition = wrap_class(class {
        constructor() {}

        acquire() {}

        wait() {}

        notify_all() {}

        release() {}
    });

    static Lock = wrap_class(class {
        constructor() {}

        acquire() {}

        release() {}        
    });

    static current_thread() { return {} } 
    static enumerate() { return [] } 
}

class time {
    static time() {
        return (new Date().getTime()) / 1000.0;
    }
}
