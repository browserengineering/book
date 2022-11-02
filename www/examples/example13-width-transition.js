div = document.querySelectorAll("div")[0];
function start_grow(e) {
		div.style = "background-color:lightblue;width:400px";
}

function start_shrink(e) {
		div.style = "background-color:lightblue;width:100px";
}

document.querySelectorAll("button")[0].addEventListener("click", start_shrink);
document.querySelectorAll("button")[1].addEventListener("click", start_grow);
