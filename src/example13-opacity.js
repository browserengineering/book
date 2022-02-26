var end_opacity = 0;
var num_animation_frames = 120;
var frames_remaining = num_animation_frames;
function animate() {
    if (frames_remaining == 0) return;
    var div = document.querySelectorAll("div")[0];
    div.style = "opacity:" +
        (frames_remaining / num_animation_frames);
    frames_remaining--;
    requestAnimationFrame(animate);
}
requestAnimationFrame(animate);
