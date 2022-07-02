// Add click handlers to open and close inline notes on small screens.
// Notes start out closed.
function addEventListeners() {
	for (let note_container of document.querySelectorAll(".note-container")) {
		note_container.addEventListener("click", (event) => {
			console.log(event.target);
			if (event.target != note_container &&
				  event.target != note_container.firstElementChild)
				return;
			let classes = note_container.classList;
			if (!classes.contains("open"))
				classes.add("open");
			else
				classes.remove("open");
			event.preventDefault();
		});
	}

 	for (let header of document.querySelectorAll("h1")) {
		header.addEventListener("click", (event) => {
 			if (header.id)
				window.location.href = `#${header.id}`;
			event.preventDefault();
		});
	}

}

window.addEventListener("load", addEventListeners);

function resize_iframes(event) {
    let elts = document.querySelectorAll("[data-big-height][data-small-height]");
    for (let elt of elts) {
        if (document.documentElement.clientWidth <= 800) {
            elt.height = elt.dataset.smallHeight;
        } else {
            elt.height = elt.dataset.bigHeight;
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
    for (var pre of pres) {
        var marks = pre.querySelectorAll("mark");
        for (var i = 0; i < marks.length; i++) {
            let [bgcolor, labelcolor] = COLORS[i % COLORS.length];
            let mark = marks[i];
            let label = mark.querySelector("label");
            mark.style["background-color"] = bgcolor;
            label.style["color"] = labelcolor;
        }
    }
}

window.addEventListener("load", resize_iframes);
window.addEventListener("resize", resize_iframes);
window.addEventListener("DOMContentLoaded", highlight_regions);

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

window.addEventListener("load", setup_close);
