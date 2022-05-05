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

var go_up = false;
var div = document.querySelectorAll("div")[0];
function go() {
	go_up = !go_up;
	if (go_up)
		div.style = "background-color:lightblue;transform:translate(0px,0px);opacity:0.1";
	else
		div.style = "background-color:lightblue;transform:translate(50px,50px);opacity:0.999";
	setTimeout(go, 16*120);
}
