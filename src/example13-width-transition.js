var count = 0
function frame() {
	if (count == 1) {
		var div = document.querySelectorAll("div")[0]
		div.style = "width:100px";
	} else {
		count++;
		requestAnimationFrame(frame);
	}
}
requestAnimationFrame(frame);

