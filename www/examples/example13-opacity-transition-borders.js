var count = 0
function frame() {
	if (count == 1) {
		go();
	} else {
		count++;
		requestAnimationFrame(frame);
	}
}
requestAnimationFrame(frame);

var go_down = false;
var div = document.querySelectorAll("#child")[0];
function go() {
	go_down = !go_down;
	if (go_down)
		div.style = "opacity:0.1";
	else
		div.style = "opacity:0.999";
	setTimeout(go, 16*120);
}
