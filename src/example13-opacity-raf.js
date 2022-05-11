var div = document.querySelectorAll("div")[0];
var total_frames = 120;
var current_frame = 0;
var change_per_frame = (0.999 - 0.1) / total_frames;

function fade_in() {
    current_frame++;
    var new_opacity = current_frame * change_per_frame + 0.1;
    div.style = "opacity:" + new_opacity;
    return current_frame < total_frames;
}

function run_fade_in() {
    if (fade_in())
        requestAnimationFrame(run_fade_in);
}

function start_fade_in(e) {
    current_frame = 0;
    requestAnimationFrame(run_fade_in);
    e.preventDefault();
}

function fade_out() {
    current_frame++;
    var new_opacity = 0.999 - current_frame * change_per_frame;
    div.style = "opacity:" + new_opacity;
    return current_frame < total_frames;
}

function run_fade_out() {
    if (fade_out())
        requestAnimationFrame(run_fade_out);
}

function start_fade_out(e) {
    current_frame = 0;
    requestAnimationFrame(run_fade_out);
    e.preventDefault();
}

document.querySelectorAll("button")[0].addEventListener("click", start_fade_out);
document.querySelectorAll("button")[1].addEventListener("click", start_fade_in);
