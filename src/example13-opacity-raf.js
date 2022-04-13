var end_value = 0.1;
var frames_remaining = 120;
var go_down = true;
function animate() {
    var div = document.querySelectorAll("div")[0];
    var percent_remaining = frames_remaining / 120;
    if (!go_down) percent_remaining = 1 - percent_remaining;
    div.style = "opacity:" +
        (percent_remaining * 0.999 +
            (1 - percent_remaining) * 0.1);
    if (frames_remaining-- == 0) {
        frames_remaining = 120;
        go_down = !go_down;
    }
    requestAnimationFrame(animate);
}
requestAnimationFrame(animate);
