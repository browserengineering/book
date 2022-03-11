
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
var div = document.querySelectorAll("div")[1];
function go() {
	go_down = !go_down;
	if (go_down)
		div.style = "background-color:lightgreen;transform:translate(0px,0px)";
	else
		div.style = "background-color:lightgreen;transform:translate(100px,-100px)";
	setTimeout(go, 2000);
}