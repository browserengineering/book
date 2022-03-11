var start_value = 1;
var end_value = 0.1;
var num_animation_frames = 120;
var frames_remaining = num_animation_frames;
var go_down = true;
function animate() {
    var div = document.querySelectorAll("div")[0];
    var percent_remaining = frames_remaining / num_animation_frames;
    if (go_down) {
        div.style = "opacity:" +
            (percent_remaining * start_value +
                (1 - percent_remaining) * end_value);
    } else {
        div.style = "opacity:" +
            ((1-percent_remaining) * start_value +
                percent_remaining * end_value);
    }
    frames_remaining--;
    if (frames_remaining < 0) {
        frames_remaining = num_animation_frames;
        go_down = !go_down;
    }
    requestAnimationFrame(animate);
}
requestAnimationFrame(animate);
