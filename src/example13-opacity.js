var start_value = 1;
var end_value = 0.1;
var num_animation_frames = 120;
var frames_remaining = num_animation_frames;
function animate() {
    if (frames_remaining == 0) return;
    var div = document.querySelectorAll("div")[0];
    var percent_remaining = frames_remaining / num_animation_frames;
    div.style = "opacity:" +
        (percent_remaining * start_value +
            (1 - percent_remaining) * end_value);
    frames_remaining--;
    requestAnimationFrame(animate);
}
requestAnimationFrame(animate);
