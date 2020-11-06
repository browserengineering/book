allow_submit = true;
p_error = document.querySelectorAll("#errors")[0];

function lengthCheck() {
    allow_submit = this.getAttribute("value").length <= 100;
    if (!allow_submit) {
        p_error.innerHTML = "Comment too long!"
    }
}

input = document.querySelectorAll("input")[0];
input.addEventListener("change", lengthCheck);

form = document.querySelectorAll("form")[0];
form.addEventListener("submit", function(e) {
    if (!allow_submit) e.preventDefault();
});
