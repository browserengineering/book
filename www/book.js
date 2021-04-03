// Add click handlers to open and close inline notes on small screens.
// Notes start out closed.
function addNoteOpeners() {
	for (let note_container of document.querySelectorAll(".note-container")) {
		note_container.addEventListener("click", (event) => {
			let classes = note_container.classList;
			if (!classes.contains("open"))
				classes.add("open");
			else
				classes.remove("open");
			event.preventDefault();
		});
	}
}

window.addEventListener("load", addNoteOpeners);
