function markdown(elt, tools) {
    if (tools) tools.remove();
    var text = elt.textContent;
    if (tools) elt.insertBefore(tools, elt.childNodes[0]);
    return text;
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

var LOCK = false;

function make_tools(node) {
    var a_typo = Element("a", { href: "#" }, "Typo" );
    var a_comment = Element("a", { href: "#" }, "Comment" );
    var form = Element("textarea", { placeholder: "Comment here" }, []);
    form.style.display = "none";
    var tools = Element("div", { className: "tools" }, [a_typo, a_comment, form]);

    a_typo.addEventListener("click", function(e) {
        LOCK = true;
        tools.remove()
        node.contentEditable = true;
        node.focus()
        var old_text = markdown(node);
        var editing = true;
        node.addEventListener("blur", function() {
            var new_text = markdown(node, tools);
            if (editing && new_text !== old_text) {
                console.log("Submitting typo correction");
                submit_typo(old_text, new_text);
            }
            editing = false;
            LOCK = false;
        });
        e.preventDefault();
    });

    a_comment.addEventListener("click", function(e) {
        form.style.display = "block";
        form.focus()
        LOCK = true;
        var editing = true;
        form.addEventListener("blur", function() {
            var comment = form.value;
            var text = markdown(node, tools);
            if (editing && text) {
                console.log("Submitting comment");
                submit_comment(text, comment);
            }
            editing = false;
            form.style.display = "none";
            form.textContent = "";
            LOCK = false;
        });
        e.preventDefault();
    });

    return tools;
}

function typo_mode() {
    var elts = document.querySelectorAll("p, li, pre, .note");
    for (var i = 0; i < elts.length; i++) {
        (function(form) {
            elts[i].addEventListener("mouseenter", function() {
                if (!LOCK) this.insertBefore(form, this.childNodes[0]);
            });
            elts[i].addEventListener("mouseleave", function() {
                if (!LOCK) form.remove();
            });
        })(make_tools(elts[i]));
    }
}

function bad_request() {
    if (this.status !== 200) {
        console.error("Something went wrong with the XHR!");
    }
}

function submit_typo(oldt, newt) {
    var xhr = new XMLHttpRequest();
    xhr.addEventListener("load", bad_request);
    xhr.open("POST", "http://127.0.0.1:8000/api/typo");
    xhr.send(JSON.stringify({'old': oldt, 'new': newt, 'url': location.pathname}));
}

function submit_comment(text, comment) {
    var xhr = new XMLHttpRequest();
    xhr.addEventListener("load", bad_request);
    xhr.open("POST", "http://127.0.0.1:8000/api/comment");
    xhr.send(JSON.stringify({'text': text, 'comment': comment, 'url': location.pathname}));
}

function feedback_mode() {
    var elts = document.querySelectorAll("button");
    for (var i = 0; i < elts.length; i++) {
        elts[i].addEventListener('click', function() {
            submit_status(parseInt(this.parentNode.dataset.id), this.className);
            this.parentNode.remove();
        });
    }
}

function submit_status(id, status) {
    var xhr = new XMLHttpRequest();
    xhr.addEventListener("load", bad_request);
    xhr.open("POST", "http://127.0.0.1:8000/api/status");
    xhr.send(JSON.stringify({'id': id, 'status': status}));
}

document.addEventListener("DOMContentLoaded", function() {
    if (document.cookie.indexOf('tools=') == -1) return;
    if (document.body.id == "feedback") feedback_mode();
    else typo_mode();
})
