var end_opacity = 0;
var num_animation_frames = 100;
function animate() {
    if (num_animation_frames == 0) return;
    var div = document.querySelectorAll("div")[0];
    div.style = "opacity:" + (num_animation_frames / 100);
    num_animation_frames--;
    requestAnimationFrame(animate);
}
requestAnimationFrame(animate);
