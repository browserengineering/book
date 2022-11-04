var div = document.querySelectorAll("div")[0];
var total_frames = 120;
var current_frame = 0;
var change_per_frame = (400 - 100) / total_frames;

function grow() {
    current_frame++;
    var new_width = current_frame * change_per_frame + 100;
    div.style = "background-color:lightblue;" + "width:" + new_width + "px";
    return current_frame < total_frames;
}

function run_grow() {
    if (grow())
        requestAnimationFrame(run_grow);
}

function start_grow(e) {
    current_frame = 0;
    requestAnimationFrame(run_grow);
    e.preventDefault();
}

function shrink() {
    current_frame++;
    var new_width = 400 - current_frame * change_per_frame;
    div.style = "background-color:lightblue;" + "width:" + new_width + "px";
    return current_frame < total_frames;
}

function run_shrink() {
    if (shrink())
        requestAnimationFrame(run_shrink);
}

function start_shrink(e) {
    current_frame = 0;
    requestAnimationFrame(run_shrink);
    e.preventDefault();
}

document.querySelectorAll("button")[0].addEventListener("click", start_grow);
document.querySelectorAll("button")[1].addEventListener("click", start_shrink);
