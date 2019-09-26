allow_submit = true;
input = document.querySelectorAll("input")[0]

function lengthCheck() {
    allow_submit = input.getAttribute("value").length <= 100;
    if (!allow_submit) {
        document.querySelectorAll("#errors")[0].innerHTML = 
            "Comment too long!"
    }
}

input.addEventListener("change", lengthCheck);

form = document.querySelectorAll("form")[0]
form.addEventListener("submit", function(e) {
    if (!allow_submit) e.preventDefault();
})
