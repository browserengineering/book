var allow_submit = true;
var p_error = document.querySelectorAll("#errors")[0];

function lengthCheck() {
    allow_submit = this.getAttribute("value").length <= 100;
    if (!allow_submit) {
        p_error.innerHTML = "Comment too long!"
    }
}

var input = document.querySelectorAll("input")[0];
if (input) {
    input.addEventListener("keydown", lengthCheck);
}

var form = document.querySelectorAll("form")[0];
if (form) {
    form.addEventListener("submit", function(e) {
        if (!allow_submit) e.preventDefault();
    });
}
