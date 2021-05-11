var count = 0;
var start_time = Date.now();
var cur_frame_time = start_time

function callback() {
	var output = document.querySelectorAll("#output")[0];
  var since_last_frame = Date.now() - cur_frame_time;
  var total_elapsed = Date.now() - start_time;
  output.innerHTML = "count: " + (count++) + "<br>" +
      " time elapsed since last frame: " + 
      since_last_frame + "ms" +
      " total time elapsed: " + total_elapsed + "ms";
	if (count <= 100)
		requestAnimationFrame(callback);
	cur_frame_time = Date.now()
}
requestAnimationFrame(callback);