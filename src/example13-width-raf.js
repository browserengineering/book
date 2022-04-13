var go_down = true;
function animate() {
    var div = document.querySelectorAll("div")[0];
    var percent_remaining = frames_remaining / 120;
    if (!go_down) percent_remaining = 1 - percent_remaining;
    div.style = "background-color:lightblue;width:" +
        (percent_remaining * 400 +
        (1 - percent_remaining) * 100) + "px";
    if (frames_remaining-- == 0) {
        frames_remaining = 120;
        go_down = !go_down;
    }
    requestAnimationFrame(animate);
}
requestAnimationFrame(animate);
