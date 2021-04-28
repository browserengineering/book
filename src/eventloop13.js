var count = 0;
var start_time = Date.now();
var cur_frame_time = start_time
console.log('start');
function callback() {
console.log('callback!!!');
	var output = document.querySelectorAll("#output")[0];
	output.innerHTML = "count: " + (count++) + "<br>" +
 		" time elapsed since last frame: " +  (Date.now() - cur_frame_time) + "ms" +
		" total time elapsed: " + (Date.now() - start_time) + "ms";
	if (count <= 1)
		requestAnimationFrame(callback);
	cur_frame_time = Date.now()
}
//requestAnimationFrame(callback);