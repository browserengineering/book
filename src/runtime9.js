console = { log: function(x) { call_python("log", x); } }

document = { querySelectorAll: function(s) {
    var handles = call_python("querySelectorAll", s)
    return handles.map(function(h) { return new Node(h) });
}}

function Node(handle) { this.handle = handle; }
Node.prototype.getAttribute = function(attr) {
    return call_python("getAttribute", self.handle, attr);
}

LISTENERS = {}

Node.prototype.addEventListener = function(type, handler) {
    if (!LISTENERS[this.handle]) LISTENERS[this.handle] = {};
    var dict = LISTENERS[this.handle]
    if (!dict[type]) dict[type] = [];
    var list = dict[type];
    list.push(handler);
}

Object.defineProperty(Node.prototype, 'innerHTML', {
    set: function(s) {
        call_python("innerHTML", this.handle, "" + s);
    }
});

function __runHandlers(handle, type) {
    var list = (LISTENERS[handle] && LISTENERS[handle][type]) || [];
    var evt = new Event(type);
    for (var i = 0; i < list.length; i++) {
        list[i].call(new Node(handle), evt);
    }
    return evt.do_default;
}

function Event(type) {
    this.type = type
    this.do_default = true;
}

Event.prototype.preventDefault = function() {
    this.do_default = false;
}
