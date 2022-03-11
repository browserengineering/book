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
var div = document.querySelectorAll("div")[0];
function go() {
	go_down = !go_down;
	if (go_down)
		div.style.opacity = "0.1";
	else
		div.style.opacity = "1.0";
	setTimeout(go, 2000);
}