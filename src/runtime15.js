window.console = { log: function(x) { call_python("log", x); } }

window.document = { querySelectorAll: function(s) {
    var handles = call_python("querySelectorAll", s, window._id);
    return handles.map(function(h) { return new Node(h) });
}}

window.Node = function(handle) { this.handle = handle; }

Node.prototype.getAttribute = function(attr) {
    return call_python("getAttribute", this.handle, attr);
}

window.LISTENERS = {}

window.Event = function(type) {
    this.type = type;
    this.do_default = true;
}

Event.prototype.preventDefault = function() {
    this.do_default = false;
}

Node.prototype.addEventListener = function(type, listener) {
    if (!LISTENERS[this.handle]) LISTENERS[this.handle] = {};
    var dict = LISTENERS[this.handle];
    if (!dict[type]) dict[type] = [];
    var list = dict[type];
    list.push(listener);
}

Object.defineProperty(Node.prototype, 'innerHTML', {
    set: function(s) {
        call_python("innerHTML_set", this.handle, s.toString());
    }
});

Object.defineProperty(Node.prototype, 'style', {
    set: function(s) {
        call_python("style_set", this.handle, s.toString());
    }
});

Node.prototype.dispatchEvent = function(evt) {
    var type = evt.type;
    var handle = this.handle
    var list = (LISTENERS[handle] && LISTENERS[handle][type]) || [];
    for (var i = 0; i < list.length; i++) {
        list[i].call(this, evt);
    }
    return evt.do_default;
}

window.SET_TIMEOUT_REQUESTS = {}

window.setTimeout = function(callback, time_delta) {
    var handle = Object.keys(SET_TIMEOUT_REQUESTS).length;
    SET_TIMEOUT_REQUESTS[handle] = callback;
    call_python("setTimeout", handle, time_delta, self._id)
}

window.__runSetTimeout = function(handle) {
    var callback = SET_TIMEOUT_REQUESTS[handle]
    callback();
}

window.XHR_REQUESTS = {}

window.XMLHttpRequest = function() {
    this.handle = Object.keys(XHR_REQUESTS).length;
    XHR_REQUESTS[this.handle] = this;
}

XMLHttpRequest.prototype.open = function(method, url, is_async) {
    this.is_async = is_async;
    this.method = method;
    this.url = url;
}

XMLHttpRequest.prototype.send = function(body) {
    this.responseText = call_python("XMLHttpRequest_send",
        this.method, this.url, this.body, this.is_async, this.handle,
        window._id);
}

window.__runXHROnload = function(body, handle) {
    var obj = XHR_REQUESTS[handle];
    var evt = new Event('load');
    obj.responseText = body;
    if (obj.onload)
        obj.onload(evt);
}

window.Date = function() {}
Date.now = function() {
    return call_python("now");
}

window.RAF_LISTENERS = [];

window.requestAnimationFrame = function(fn) {
    RAF_LISTENERS.push(fn);
    call_python("requestAnimationFrame");
}

window.__runRAFHandlers = function() {
    var handlers_copy = [];
    for (var i = 0; i < RAF_LISTENERS.length; i++) {
        handlers_copy.push(RAF_LISTENERS[i]);
    }
    RAF_LISTENERS = [];
    for (var i = 0; i < handlers_copy.length; i++) {
        handlers_copy[i]();
    }
}

window.WINDOW_LISTENERS = {}

window.PostMessageEvent = function(data) {
    this.type = "message";
    this.data = data;
}

Window.prototype.postMessage = function(message, domain) {
    call_python("postMessage", this._id, message, domain)
}

Window.prototype.addEventListener = function(type, listener) {
    if (!WINDOW_LISTENERS[this.handle]) WINDOW_LISTENERS[this.handle] = {};
    var dict = WINDOW_LISTENERS[this.handle];
    if (!dict[type]) dict[type] = [];
    var list = dict[type];
    list.push(listener);
}

Window.prototype.dispatchEvent = function(evt) {
    var type = evt.type;
    var handle = this.handle
    var list = (WINDOW_LISTENERS[handle] && WINDOW_LISTENERS[handle][type]) || [];
    for (var i = 0; i < list.length; i++) {
        list[i].call(this, evt);
    }

    return evt.do_default;
}

Object.defineProperty(Window.prototype, 'parent', {
  configurable: true,
  get: function() {
    parent_id = call_python('parent', window._id);
    if (parent_id != undefined) {
        try {
            target_window = eval("window_" + parent_id);
            // Same-origin
            return target_window;
        } catch (e) {
            // Cross-origin
            return new Window(-1)
        }

    }
    return undefined;
  }
});
