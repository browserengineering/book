var frames_remaining = 120;
var go_down = true;
var div = document.querySelectorAll("div")[0];
function animate() {
    var percent_remaining = frames_remaining / 120;
    if (!go_down) percent_remaining = 1 - percent_remaining;
    div.style = "opacity:" +
        (percent_remaining * 0.999 +
            (1 - percent_remaining) * 0.1);
    if (frames_remaining-- == 0) {
        go_down = !go_down
        frames_remaining = 120;
    }
    return true;
}

function run_animation_frame() {
    if (animate())
        requestAnimationFrame(run_animation_frame);
}
requestAnimationFrame(run_animation_frame);
