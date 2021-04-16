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

window.addEventListener("load", resize_iframes);
window.addEventListener("resize", resize_iframes);
