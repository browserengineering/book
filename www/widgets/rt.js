/* This file simulates Python packages used by the WBE browser */


export { breakpoint, comparator, filesystem, http_textarea, lib, pysplit,
    pyrsplit, rt_constants, socket, ssl, tkinter, truthy, Widget };

window.TKELEMENT = null;

function wrap_class(cls) {
    return function(...args) {
        return new cls(...args);
    }
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
rt_constants.TKELEMENT = null;
rt_constants.URLS = {};

class ExpectedError extends Error {
    constructor(msg) {
        super(msg);
    }
}

class WidgetXHRError extends ExpectedError {
    constructor(hostname) {
        super("This widget cannot access " + hostname + " due to sandboxing, " +
              "but the underlying Python code should work correctly.");
        this.name = "WidgetXHRError";
    }
}

class lib {

static socket(URLS) {
    class socket {
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
            console.assert(params.encoding == "utf8" && params.newline == "\r\n", "Unknown socket encoding or line ending");
            console.assert(mode == "r", "Unknown socket makefile mode");

            let [line1] = this.input.split("\r\n", 1);
            let [method, path, protocol] = line1.split(" ");
            this.url = this.scheme + "://" + this.host + path;
            if (rt_constants.URLS[this.url]) {
                var response = rt_constants.URLS[this.urls];
                this.output = typeof response === "function" ? response() : response;
                this.idx = 0;
                this.closed = false;
            } else if (this.host == "browser.engineering") {
                let response = await fetch(path);
                this.output = "HTTP/1.0 " + response.status + " " + response.statusText + "\r\n";
                for (let [header, value] of response.headers.entries()) {
                    this.output += header + ": " + value + "\r\n";
                }
                this.output += "\r\n";
                this.output += await response.text();
                this.closed = false;
                this.idx = 0;
                return this;
            } else {
                console.log(this);
                throw new WidgetXHRError(this.host);               
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
    }
    
    return {socket: wrap_class(socket), AF_INET: "inet", SOCK_STREAM: "stream", IPPROTO_TCP: "tcp"}
}

static ssl() {
    class context {
        wrap_socket(s, params) {
            console.assert(s.host == params.server_hostname, "Invalid SSL server name, does not match socket host");
            s.scheme = "https";
            return s;
        }
    }
    return { create_default_context: wrap_class(context) };
}

static tkinter(options) { 
    class Tk {
        constructor() {
            this.elt = rt_constants.TKELEMENT;
        }

        bind(key, fn) {
            if (['<Up>', '<Down>', '<Left>', '<Right>'].indexOf(key) !== -1) {
                window.addEventListener("keydown", function(e) {
                    if (e.key == 'Arrow' + key.substr(1, key.length-2)) {
                        e.preventDefault();
                        fn({}).catch(on_error);
                    }
                });
            } else if (key == '<Return>') {
                window.addEventListener("keydown", function(e) {
                    if (e.key == 'Enter') {
                        e.preventDefault();
                        fn({}).catch(on_error);
                    }
                });
            } else if (['<Button-1>', '<Button-2>', '<Button-3>'].indexOf(key) !== -1) {
                window.addEventListener("mousedown", function(e) {
                    if (e.button == key.substr(8, 1) - 1) {
                        fn({ x: e.offsetX, y: e.offsetY }).catch(on_error);
                    }
                });
            } else if (key == '<Configure>') {
                window.addEventListener("resize", function(e) {
                    fn({}).catch(on_error);
                });
            } else if (key == '<Key>') {
                window.addEventListener("keydown", function(e) {
                    if (e.key.length == 1) {
                        e.preventDefault();
                        fn({ char: e.key }).catch(on_error);
                    };
                });
            } else if (key.length == 1) {
                window.addEventListener("keydown", function(e) {
                    if (e.key == key) {
                        e.preventDefault();
                        fn({ char: e.key }).catch(on_error);
                    }
                });
            } else {
                console.error("Trying to bind unsupported event", key);
            }
        }
    }

    class Canvas {
        constructor(tk, params) {
            this.tk = tk;
            this.tk.elt.width = params.width * rt_constants.ZOOM;
            this.tk.elt.height = params.height * rt_constants.ZOOM;
            this.ctx = tk.elt.getContext('2d');
            this.ctx.font = "normal normal " + 16 * rt_constants.ZOOM + "px serif"
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
    }
    
    class Font {
        constructor(params) {
            this.size = params.size ?? 16;
            this.weight = params.weight ?? "normal";
            this.style = params.style ?? "normal";
            this.string = (this.style == "roman" ? "normal" : this.style) + 
                " " + this.weight + " " + this.size * rt_constants.ZOOM + "px serif";

            this.$metrics = null;
        }

        measure(text) {
            let ctx = rt_constants.TKELEMENT.getContext('2d');
            ctx.font = this.string;
            return ctx.measureText(text).width / rt_constants.ZOOM;
        }

        metrics(field) {
            if (!this.$metrics) {
                let ctx = rt_constants.TKELEMENT.getContext('2d');
                ctx.textBaseline = "alphabetic";
                ctx.font = this.string;
                let m = ctx.measureText("Hxy");
                let asc, desc;

                // Only Safari provides emHeight properties as of 2021-04
                // We fake them in the other browsers by guessing that emHeight = font.size
                // This is not quite right but is close enough for many fonts...
                if (m.emHeightAscent && m.emHeightDescent) {
                    asc = ctx.measureText("Hxy").emHeightAscent / rt_constants.ZOOM;
                    desc = ctx.measureText("Hxy").emHeightDescent / rt_constants.ZOOM;
                } else {
                    asc = ctx.measureText("Hxy").actualBoundingBoxAscent / rt_constants.ZOOM;
                    desc = ctx.measureText("Hxy").actualBoundingBoxDescent / rt_constants.ZOOM;
                    let gap = this.size - (asc + desc)
                    asc += gap / 2;
                    desc += gap / 2;
                }
                this.$metrics = { ascent: asc, descent: desc, linespace: asc + desc, fixed: 0 };
            }
            if (field) return this.$metrics[field]
            else return this.$metrics;
        }
    }

    return {Tk: wrap_class(Tk), Canvas: wrap_class(Canvas), font: { Font: wrap_class(Font) }}
}

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
            alert(e);
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

class File {
    constructor(contents) {
        this.contents = contents;
    }
    read() {
        return this.contents;
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
    open(name) {
        return new File(this.files[name]);
    }
}

const filesystem = new FileSystem();

const socket = lib.socket();
const ssl = lib.ssl();
const tkinter = lib.tkinter();
