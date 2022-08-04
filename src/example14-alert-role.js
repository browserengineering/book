div = document.querySelectorAll("div")[0]
button = document.querySelectorAll("button")[0]
button.addEventListener("click", onclick);
function onclick(e) {
	if (!div.getAttribute("role"))
		div.setAttribute("role", "alert");
	else
		div.setAttribute("role", "");
	e.preventDefault();
}
