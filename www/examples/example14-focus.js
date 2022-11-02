var link = document.querySelectorAll("a")[0];
link.addEventListener("click", prevent);
function prevent(e) {
	console.log('hi');
	e.preventDefault();
}