var frames_remaining = 120;
var go_down = true;
var div = document.querySelectorAll("div")[0];
function animate() {
    var percent_remaining = frames_remaining / 120;
    if (!go_down) percent_remaining = 1 - percent_remaining;
    div.style = "background-color:lightblue;width:" +
        (percent_remaining * 400 +
        (1 - percent_remaining) * 100) + "px";
    if (frames_remaining-- == 0) {
        frames_remaining = 120;
        go_down = !go_down;
    }
    return true;
}

function run_animation_frame() {
    if (animate())
        requestAnimationFrame(run_animation_frame);
}
requestAnimationFrame(run_animation_frame);
