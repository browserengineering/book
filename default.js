node_store = {}

document = {
    querySelector: function(s) {
        var h = call_python('querySelector', s);
        var o = {
            set innerHTML(src) { call_python('innerHTML', h, src) },
            addEventListener: function(type, fn) {
                this.listeners.push([type, fn]);
            },
            getAttribute: function(attr) { return call_python('get_attr', h, attr); },
            get value() { return this.getAttribute("value"); },
            listeners: []
        };
        node_store[h] = o;
        return o;
    }
}

console = {
    log: function(s) { call_python('log', s) }
}

function _handle_event(handle, data) {
    var elt = node_store[handle];
    var type = data.type;
    for (var i = 0; i < elt.listeners.length; i++) {
        if (elt.listeners[i][0] == type) {
            elt.listeners[i][1](data);
        }
    }
}
