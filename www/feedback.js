
// Thanks for reading the code! You can hit Ctrl+E to access the feedback tools.

document.addEventListener("DOMContentLoaded", function() {
    if (window.localStorage["edit"] == "true") return typo_mode();

    window.addEventListener("keydown", function(e) {
        if (String.fromCharCode(e.keyCode) != "E") return;
        if (!(e.metaKey || e.ctrlKey)) return;
        e.preventDefault();
        setup_feedback();
    });
});

var EDITABLE_ELEMENTS = "p, li, pre, .note";

function markdown(elt, arr, recursive) {
    if (elt.nodeType == Node.TEXT_NODE) {
        arr.push(elt.textContent);
    } else if (elt.nodeType == Node.ELEMENT_NODE) {
        if (recursive && elt.matches(EDITABLE_ELEMENTS)) {
            arr.push("[*]");
        } else {
            for (var i = 0; i < elt.childNodes.length; i++) {
                markdown(elt.childNodes[i], arr, true);
            }
        }
    } else {
        // Skip weird nodes
    }
    return arr;
}

function Element(name, properties, children) {
    if (!children) { children = properties; properties = {} }
    var elt = document.createElement(name);
    for (var i in properties) {
        if (properties.hasOwnProperty(i)) elt[i] = properties[i];
    }
    function recurse(child) {
        if (!child) return;
        else if (Array.isArray(child)) child.map(recurse);
        else if (typeof child === "string") elt.appendChild(document.createTextNode(child));
        else elt.appendChild(child);
    }
    recurse(children);
    return elt
}

function Tools() {
    var a_typo = Element("a", { href: "#" }, "Typo" );
    var a_comment = Element("a", { href: "#" }, "Comment" );

    this.form = Element("textarea", {
        style: "display: none",
        placeholder: "Comment here",
    }, []);

    this.toolbar = Element("div", { className: "tools" }, [a_typo, a_comment, this.form]);

    this.lock = false;
    this.node = null;

    a_typo.addEventListener("click", this.typo.bind(this));
    a_comment.addEventListener("click", this.comment.bind(this));
}

Tools.prototype.typo = function(e) {
    var that = this;
    that.lock = true;
    that.toolbar.remove()
    that.node.contentEditable = true;
    that.node.focus()
    var old_text = markdown(that.node, []).join("");
    var editing = true;
    that.node.addEventListener("blur", function() {
        var new_text = markdown(that.node, []).join("");
        if (editing && new_text !== old_text) {
            submit_typo(old_text, new_text);
        }
        that.node.contentEditable = false;
        editing = false;
        that.lock = false;
    });
    e.preventDefault();
}

Tools.prototype.comment = function(e) {
    var that = this;
    that.form.style.display = "block";
    that.form.focus()
    that.lock = true;
    var editing = true;
    that.form.addEventListener("blur", function() {
        var comment = that.form.value;
        var text = markdown(that.node, []).join("");
        if (editing && comment) {
            console.log("Submitting comment");
            submit_comment(text, comment);
        }
        editing = false;
        that.form.style.display = "none";
        that.form.value = "";
        that.lock = false;
    });
    e.preventDefault();
}

Tools.prototype.attach = function(node, e) {
    if (this.lock) return;
    this.node = node;
    this.node.insertBefore(this.toolbar, this.node.childNodes[0]);
}

Tools.prototype.remove = function(e) {
    if (this.lock) return;
    this.node = false;
    this.toolbar.remove();
}

function typo_mode() {
    var elts = document.querySelectorAll(EDITABLE_ELEMENTS);
    var tools = new Tools(elts[i]);
    for (var i = 0; i < elts.length; i++) {
        elts[i].addEventListener("mouseenter", tools.attach.bind(tools, elts[i]));
        elts[i].addEventListener("mouseleave", tools.remove.bind(tools));
    }
}

function bad_request() {
    if (this.status === 200) return;
    console.error("Something went wrong with the XHR!");
}

function submit_typo(oldt, newt) {
    var xhr = new XMLHttpRequest();
    xhr.addEventListener("load", bad_request);
    xhr.open("POST", "/api/typo");
    xhr.send(JSON.stringify({
        'old': oldt,
        'new': newt,
        'url': location.pathname,
        'name': window.localStorage["name"],
    }));
}

function submit_comment(text, comment) {
    var xhr = new XMLHttpRequest();
    xhr.addEventListener("load", bad_request);
    xhr.open("POST", "/api/comment");
    xhr.send(JSON.stringify({
        'text': text,
        'comment': comment,
        'url': location.pathname,
        'name': window.localStorage["name"],
    }));
}

function setup_feedback() {
    var submit = Element("button", { type: "submit" }, "Turn on feedback tools");
    var cancel = Element("a", { href: "#" }, "Keep feedback tools off");
    var form = Element("div", { className: "popup" }, [
        Element("form", { method: "get", action: "/" }, [
            Element("h1", "Feedback Tools"),
            Element("p", [
                "You've pressed ", Element("kbd", "Ctrl+E"), ",",
                "which enables ", Element("i", "feedback tools"), ". ",
                "You can use them to ",
                Element("em", "fix typos"), " and ",
                Element("em", "leave comments"), " on the text. ",
                "I review the feedback to improve the book.",
            ]),
            Element("div", { className: "inputs" }, [
                Element("label", { "for": "name" }, "Your name: "),
                Element("input", { name: "name", autofocus: "", required: "" }, []),
            ]),
            Element("p", { className: "legalese" }, [
                "By making edits, you agree to assign all rights ",
                "to your comments or typo fixes to me (Pavel Panchekha)",
                "and allow me to attribute edits to you in acknowledgements, ",
                "blog posts, or other media.",
            ]),
            Element("div", { className: "buttons" }, [submit, cancel]),
        ]),
    ]);
    var overlay = Element("div", { id: "overlay" }, [form]);

    function do_submit(e) {
        window.localStorage["edit"] = "true";
        window.localStorage["name"] = this.querySelector("input").value;
        e.preventDefault();
        typo_mode();
        overlay.remove();
    }
    
    function do_cancel(e) {
        overlay.remove();
    }

    form.addEventListener("submit", do_submit);
    overlay.addEventListener("click", do_cancel);
    cancel.addEventListener("click", do_cancel);
    form.addEventListener("click", function(e) { e.stopPropagation(); });

    document.documentElement.appendChild(overlay);
}
