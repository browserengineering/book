/* NOTE: because this is deployed to browser.engineering, this must use
 * only old-school JavaScript supported by DukPy, including no `let`, no
 * `for of`, no arrow functions, and so on.
 *
 * Also there is no `window` object in early versions of the browser; so
 * any references to window.addEventListener need to be guarded. */

// Add click handlers to open and close inline notes on small screens.
// Notes start out closed.
function addEventListeners() {
        var containers = document.querySelectorAll(".note-container")
	for (var i = 0; i < containers.length; i++) {
	    var callback = (function(note_container) {
		return function (event) {
			if (event.target != note_container &&
				  event.target != note_container.firstElementChild)
				return;
			var classes = note_container.classList;
			if (!classes.contains("open"))
				classes.add("open");
			else
				classes.remove("open");
			event.preventDefault();
		}
	    })(containers[i]);
	    containers[i].addEventListener("click", callback);
	}

        var headers = document.querySelectorAll("h1");
 	for (var i = 0; i < headers.length; i++) {
	    var callback = (function(header) {
		return function(event) {
 			if (header.id)
				window.location.href = "#" + header.id;
			event.preventDefault();
		}
	    })(headers[i])
	    headers[i].addEventListener("click", callback);
	}

}

if (globalThis.window && window.addEventListener)
    window.addEventListener("load", addEventListeners);

function resize_iframes(event) {
    var elts = document.querySelectorAll("[data-big-height][data-small-height]");
    for (var i = 0; i < elts.length; i++) {
        if (document.documentElement.clientWidth <= 800) {
            elts[i].height = elt.dataset.smallHeight;
        } else {
            elts[i].height = elt.dataset.bigHeight;
        }
    }
}

const COLORS = [
    ["#B5DEFF", "#064663"], // blue
    ["#FAF0AF", "#E1701A"], // yellow
    ["#FFC4E1", "#9A0680"], // pink
    ["#F4D19B", "#7D0633"], // brown
    ["#C1FFD7", "#1E5128"], // green
    ["#CAB8FF", "#4C0070"], // purple
    ["#E2C2B9", "#734046"], // brown
];

function highlight_regions() {
    var pres = document.querySelectorAll(".highlight-region");
    for (var j = 0; j < pres.length; j++) {
	var pre = pres[j];
        var marks = pre.querySelectorAll("mark");
        for (var i = 0; i < marks.length; i++) {
            var color_entry = COLORS[i % COLORS.length];
	    var bgcolor = color_entry[0], labelcolor = color_entry[1];
            var mark = marks[i];
            var label = mark.querySelector("label");
            mark.style["background-color"] = bgcolor;
            label.style["color"] = labelcolor;
        }
    }
}

if (globalThis.window && window.addEventListener) {
    window.addEventListener("load", resize_iframes);
    window.addEventListener("resize", resize_iframes);
    window.addEventListener("DOMContentLoaded", highlight_regions);
}

function close_signup(e) {
    window.localStorage["signup"] = "close";
    this.parentNode.remove();
    if (e) e.preventDefault();
}

function setup_close() {
    var close = document.querySelector("#signup-close");
    if (!close) return;
    if (window.localStorage["signup"] == "close") {
        close_signup.bind(close)();
    } else {
        close.addEventListener("click", close_signup);
    }
}

if (globalThis.window && window.addEventListener)
    window.addEventListener("DOMContentLoaded", setup_close);

// Return UUID for user; generate and store in local storage if first time
function get_or_set_id() {
  const id_key = "userUUID";
  const current_id = localStorage.getItem(id_key);

  if (typeof current_id != "string") {
    const new_id = crypto.randomUUID();
    localStorage.setItem(id_key, new_id);
    return new_id;
  } else {
    return current_id;
  }
}

function quiz_telemetry(event_type, event_payload) {
  event_payload.userId = get_or_set_id();
  if (event_type === "answers") {
    fetch("/api/quiz_telemetry", {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(event_payload)
    }).catch(function (err) { console.error('Quiz telemetry error', err); });
  }
}

// The quiz code picks this function up out of the window object
if (globalThis.window)
    window.telemetry = { log: quiz_telemetry };
