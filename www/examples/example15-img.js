document.querySelectorAll("img")[0].addEventListener("click", function(e) {
	console.log("clicked");
	e.preventDefault();
});

var parentWindow = window.parent;

if (parentWindow)
	parentWindow.postMessage("This is the contents of postMessage.", "*");

