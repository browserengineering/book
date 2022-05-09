var div = document.querySelectorAll("div")[0];
var total_frames = 120;
var current_frame = 0;
var change_per_frame = 0.999 / total_frames;
function animate() {
    current_frame++;
    var new_opacity = current_frame * change_per_frame;
    div.style = "opacity:" + new_opacity;
    return current_frame < total_frames;
}

function run_animation_frame() {
    if (animate())
        requestAnimationFrame(run_animation_frame);
}
requestAnimationFrame(run_animation_frame);
