var div = document.querySelectorAll("div")[0];

function start_fade_out(e) {
	div.style = "opacity:0.1";
  e.preventDefault();
}
function start_fade_in(e) {
	div.style = "opacity:0.999";
  e.preventDefault();
}

document.querySelectorAll("button")[0].addEventListener("click", start_fade_out);
document.querySelectorAll("button")[1].addEventListener("click", start_fade_in);
