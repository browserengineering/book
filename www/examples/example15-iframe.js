window.addEventListener("message", function(e) {
	window.console.log("Message received from iframe: " + e.data);
}, false);
