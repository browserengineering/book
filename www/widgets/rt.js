/* This file simulates Python packages used by the WBE browser */

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

class lib {

static socket(URLS) {
    class socket {
        constructor(af, sock, proto) {
            console.assert(af == "inet" && sock == "stream" && proto == "tcp", "Unknown socket triple");
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
        makefile(mode, encoding, newline) {
            console.assert(encoding == "utf8" && newline == "\r\n", "Unknown socket encoding or line ending");
            console.assert(mode == "r", "Unknown socket makefile mode");

            let [line1] = this.input.split("\r\n", 1);
            let [method, path, protocol] = line1.split(" ");
            this.url = this.scheme + "://" + this.host + path;
            this.output = URLS[this.url];
            if (!this.output) {
                throw Error("Unknown URL " + this.url);               
            } else if (typeof this.output === "function") {
                this.output = this.output();
            }
            this.idx = 0;
            this.closed = false;
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
        wrap_socket(s, host) {
            console.assert(s.host == host, "Invalid SSL server name, does not match socket host");
            s.scheme = "https";
        }
    }
    return { create_default_context: wrap_class(context) };
}

static tkinter(options) {
    let TKELEMENT = options?.canvas ?? document.createElement("canvas");
    let ZOOM = options?.zoom ?? 1.0;

    class Tk {
        constructor() {
            this.elt = TKELEMENT;
        }

        bind(key, fn) {
            // this.tk.addEventListener(...)
        }
    }

    class Canvas {
        constructor(tk, w, h) {
            this.tk = tk;
            this.tk.elt.width = w * ZOOM;
            this.tk.elt.height = h * ZOOM;
            this.ctx = tk.elt.getContext('2d');
            this.ctx.font = "normal normal " + 16 * ZOOM + "px serif"
        }

        pack() {}

        delete(who) {
            console.assert(who === "all", "tkinter.Canvas.delete expects argument 'all'");
            this.ctx.clearRect(0, 0, this.tk.elt.width, this.tk.elt.height);
        }

        create_text(x, y, txt, font, anchor) {
            if (anchor == "nw") {
                this.ctx.textAlign = "left";
                this.ctx.textBaseline = "top";
            } else {
                this.ctx.textAlign = "center";
                this.ctx.textBaseline = "middle";
            }
            if (font) this.ctx.font = font.string;
            this.ctx.fillText(txt, x * ZOOM, y * ZOOM);
        }
    }
    
    class Font {
        constructor(size, weight, style) {
            this.size = size;
            this.weight = weight;
            this.style = style;
            this.string = (this.style == "roman" ? "normal" : this.style) + 
                " " + this.weight + " " + this.size * ZOOM + "px serif";
        }

        measure(text) {
            let ctx = TKELEMENT.getContext('2d');
            ctx.font = this.string;
            return ctx.measureText(text).width / ZOOM;
        }

        metrics(field) {
            let ctx = TKELEMENT.getContext('2d');
            ctx.textBaseline = "alphabetic";
            ctx.font = this.string;
            let m = ctx.measureText("Hxy");
            let asc, desc;

            // Only Safari provides emHeight properties as of 2021-04
            // We fake them in the other browsers by guessing that emHeight = font.size
            // This is not quite right but is close enough for many fonts...
            if (m.emHeightAscent && m.emHeightDescent) {
                asc = ctx.measureText("Hxy").emHeightAscent / ZOOM;
                desc = ctx.measureText("Hxy").emHeightDescent / ZOOM;
            } else {
                asc = ctx.measureText("Hxy").actualBoundingBoxAscent / ZOOM;
                desc = ctx.measureText("Hxy").actualBoundingBoxDescent / ZOOM;
                let gap = this.size - (asc + desc)
                asc += gap / 2;
                desc += gap / 2;
            }
            let obj = { ascent: asc, descent: desc, linespace: asc + desc, fixed: 0 };
            if (field) return obj[field]
            else return obj;
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
        this.controls.reset.disabled = true;
        this.controls.back.disabled = true;
        this.controls.input.disabled = false;
        this.controls.next.disabled = false;
        this.controls.animate.disabled = false;
        this.controls.next.children[0].textContent = "Start";
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
        this.controls.next.children[0].textContent = "Next";
        this.controls.input.disabled = true;
        this.controls.reset.disabled = false;
        this.controls.back.disabled = false;
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
        this.controls.next.disabled = true;
        this.controls.animate.disabled = true;
    }

    run(k) {
        let that = this;
        this.runner = async function() {
            await k();
            that.end();
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

class FileSystem {
    class File {
        constructor(contents) {
            this.contents = contents;
        }
        read() {
            return this.contents;
        }
    }

    constructor() {
        this.files = {};
    }
    register(name, contents) {
        this.files[name] = contents;
    }
    open(name) {
        return File(this.files[name]);
    }
}

const filesystem = FileSystem();
