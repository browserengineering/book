var start_value = 400;
var end_value = 100;
var num_animation_frames = 120;
var frames_remaining = num_animation_frames;
function animate() {
    if (frames_remaining == 0) return;
    var div = document.querySelectorAll("div")[0];
    var percent_remaining = frames_remaining / num_animation_frames;
    div.style = "background-color:lightblue;width:" +
        (percent_remaining * start_value +
        (1 - percent_remaining) * end_value) + "px";
    frames_remaining--;
    requestAnimationFrame(animate);
}
requestAnimationFrame(animate);
