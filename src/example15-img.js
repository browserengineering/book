var parentWindow = window.parent;

if (parentWindow)
	postMessage("This is the contents of postMessage.", "*");
