var count = 0;
var start_time = Date.now();
var cur_frame_time = start_time;

artificial_delay_ms = 200;

function callback() {
    if (count == 0)
        requestXHR();

    var since_last_frame = Date.now() - cur_frame_time;
    while (since_last_frame < artificial_delay_ms) {
        var since_last_frame = Date.now() - cur_frame_time;
    }
    var total_elapsed = Date.now() - start_time;
    var output = document.querySelectorAll("div")[1];
    output.innerHTML = "count: " + (count++);
    if (count < 100)
        requestAnimationFrame(callback);
    cur_frame_time = Date.now()
}
requestAnimationFrame(callback);

var request;
function requestXHR() {
    request = new XMLHttpRequest();
    request.open('GET', '/xhr', true);
    request.onload = function(evt) {
        document.querySelectorAll("div")[2].innerHTML = 
            "XHR result: " + this.responseText;
    };
    request.send();
}