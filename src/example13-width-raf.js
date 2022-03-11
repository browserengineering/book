var start_value = 400;
var end_value = 100;
var num_animation_frames = 120;
var frames_remaining = num_animation_frames;
var go_down = true;
function animate() {
    var div = document.querySelectorAll("div")[0];
    var percent_remaining = frames_remaining / num_animation_frames;
    if (go_down) {
        div.style = "background-color:lightblue;width:" +
            (percent_remaining * start_value +
            (1 - percent_remaining) * end_value) + "px";
    } else {
        div.style = "background-color:lightblue;width:" +
            ((1 - percent_remaining) * start_value +
             percent_remaining * end_value) + "px";
    }
    frames_remaining--;
    if (frames_remaining < 0) {
        frames_remaining = num_animation_frames;
        go_down = !go_down;
    }
    requestAnimationFrame(animate);
}
requestAnimationFrame(animate);
