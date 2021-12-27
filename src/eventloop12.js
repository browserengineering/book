var count = 0;
var start_time = Date.now();
var cur_frame_time = start_time;

artificial_delay_ms = 200;

function callback() {
    var since_last_frame = Date.now() - cur_frame_time;
    while (since_last_frame < artificial_delay_ms) {
        var since_last_frame = Date.now() - cur_frame_time;
    }
    var total_elapsed = Date.now() - start_time;
    var output = document.querySelectorAll("div")[1];
    output.innerHTML = "count: " + (count++) + "<br>" +
        " time elapsed since last frame: " + 
        since_last_frame + "ms" +
        " total time elapsed: " + total_elapsed + "ms";
    if (count < 100)
        requestAnimationFrame(callback);
    cur_frame_time = Date.now()
}
requestAnimationFrame(callback);

request = new XMLHttpRequest()
request.open('GET', '/', true);
request.send()