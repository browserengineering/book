var count = 0;
var start_time = Date.now();
var cur_frame_time = start_time

function callback() {
	var output = document.querySelectorAll("#output")[0];
	var diff = Date.now() - cur_frame_time;
	output.innerHTML = "count: " + (count++) + "<br>" +
		" time elapsed since last frame: " +  (Date.now() - cur_frame_time) + "ms" +
		" total time elapsed: " + (Date.now() - start_time) + "ms";
	if (count <= 100)
		requestAnimationFrame(callback);
	cur_frame_time = Date.now()
}
requestAnimationFrame(callback);