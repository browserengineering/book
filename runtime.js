console = { log: function(x) { call_python("log", x); } }

document = {
    querySelectorAll: function(s) {
        return call_python("querySelectorAll", s).map(function(h) {
            return new Node(h);
        });
    },
    createElement: function(t) {
        return new Node(call_python("createElement", t));
    },
}

function Node(handle) { this.handle = handle; }
Node.prototype.getAttribute = function(attr) {
    return call_python("getAttribute", this.handle, attr);
}
Node.prototype.getAttribute = function(attr, value) {
    return call_python("setAttribute", this.handle, attr, value);
}


LISTENERS = {}

Node.prototype.addEventListener = function(type, handler) {
    if (!LISTENERS[this.handle]) LISTENERS[this.handle] = {};
    var dict = LISTENERS[this.handle]
    if (!dict[type]) dict[type] = [];
    var list = dict[type];
    list.push(handler);
}

Node.prototype.appendChild = function(child) {
    call_python("appendChild", this.handle, child.handle);
}

Node.prototype.insertBefore = function(child, sibling) {
    call_python("insertBefore", this.handle, sibling.handle, child.handle);
}

Node.prototype.getContext = function(type) {
    if (type != "2d" && type != "2D") throw "Invalid context type";
    return Context(this);
}

function Context(node) { this.node = node; }
Context.prototype.fillRect = function(x1, y1, w, h) {
    call_python("fillRect", this.node.handle, x1, y1, w, h)
}
Context.prototype.fillText = function(text, x, y) {
    call_python("fillText", this.node.handle, text, x, y)
}

Object.defineProperty(Node.prototype, 'innerHTML', {
    set: function(s) {
        call_python("innerHTML", this.handle, s);
    }
})

Object.defineProperty(Node.prototype, 'children', {
    get: function(s) {
        call_python("children", this.handle)
            .map(function(h) { return new Node(h); });
    }
})

function Event() { this.cancelled = false; this.propagating = true }
Event.prototype.preventDefault = function() { this.cancelled = true; }
Event.prototype.stopPropagation = function() { this.propagating = true; }

function __runHandlers(handle, type) {
    if (!LISTENERS[handle]) LISTENERS[handle] = {};
    var dict = LISTENERS[handle]
    if (!dict[type]) dict[type] = [];
    var list = dict[type];
    var evt = new Event()
    for (var i = 0; evt.propagating && i < list.length; i++) {
        list[i](evt);
    }
    return [evt.cancelled, this.propagating];
}

Timeouts = []
function setTimeout(ms, f) {
    var thandle = Timeouts.length;
    Timeouts.push(f);
    call_python("setTimeout", ms, thandle);
}

function __runTimer(handle) {
    Timeouts[handle]();
}

XHRs = []

function XMLHttpRequest() {
    XHRs.append(this);
    this.id = XHRs.length - 1;
    this.listeners = [];
}

XMLHttpRequest.prototype.open = function(method, url) {
    this.method = method;
    this.url = url;
}

XMLHttpRequest.prototype.send = function(body) {
    call_python("XMLHttpRequest_send", this.method, this.url, body || null, this.id);
}

XMLHttpRequest.prototype.addEventListener = function(type, f) {
    if (type == "load") this.listeners.append(f)
}

XMLHttpRequest.prototype.getResponseHeader = function(type) {
    return this.headers[type.lower()];
}

function __runXHR(id, headers, body) {
    this.headers = headers;
    this.response = this.responseText = body;
    // Lies
    this.status = 200;
    this.statusText = "OK";
    this.readyState = 4;

    var ls = XHRs[id].listeners;
    for (var i = 0; i < ls.length; i++) {
        ls[i]();
    }
}
