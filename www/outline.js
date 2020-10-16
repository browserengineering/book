OUTLINES = null;
WRITTEN = null;

function write_outlines() {
    if (!OUTLINES) return;
    if (WRITTEN) return;
    WRITTEN = true;

    var outlines = document.querySelectorAll(".outline");
    for (var i = 0; i < outlines.length; i++) {
        var src = outlines[i].dataset.file;
        if (!src || !OUTLINES[src]) throw Error("Cannot find outline data for " + src);
        console.log(src, OUTLINES[src]);
        write_outline(outlines[i], OUTLINES[src]);
    }
}

function span(cls, name) {
    var item = document.createElement("span");
    item.textContent = name;
    item.setAttribute("class", cls);
    return item;
}

function text(name) {
    return document.createTextNode(name);
}

function make_div(data) {
    var item = document.createElement("code");
    item.setAttribute("class", data.type);
    if (data.type == "ifmain") {
        item.appendChild(span("kw", "if"));
        item.appendChild(text(" __name__ "));
        item.appendChild(span("op", "=="));
        item.appendChild(text(" "));
        item.appendChild(span("st", "\"__main__\""));
        item.appendChild(text(": "));
        item.appendChild(span("co", "..."));
    } else if (data.type == "const") {
        item.appendChild(text(data.names.join(", ") + " "));
        item.appendChild(span("op", "="));
        item.appendChild(text(" "));
        item.appendChild(span("co", "..."));
    } else if (data.type == "function") {
        item.appendChild(span("kw", "def"));
        item.appendChild(text(" " + data.name + "(" + data.args.join(", ") + "): "));
        item.appendChild(span("co", "..."));
            } else if (data.type == "class") {
        item.appendChild(span("kw", "class"));
        item.appendChild(text(" " + data.name + ": "));
        item.appendChild(span("co", "..."));
        for (var i = 0; i < data.fns.length; i++) {
            item.appendChild(make_div(data.fns[i]));
        }
    }
    return item;
}

function write_outline(elt, data) {
    for (var i = 0; i < data.length; i++) {
        elt.appendChild(make_div(data[i]));
    }
}

function save_outline(data) {
    OUTLINES = data;
    write_outlines();
}

window.addEventListener("load", write_outlines);
