var allow_submit = true;
var label = document.querySelectorAll("label")[0];

function lengthCheck() {
    var value = this.getAttribute("value");
    allow_submit = value.length <= 100;
    if (!allow_submit) {
        label.innerHTML = "Comment too long!";
    } else {
        label.innerHTML = "";
    }
}

var inputs = document.querySelectorAll("input");
for (var i = 0; i < inputs.length; i++) {
    inputs[i].addEventListener("keydown", lengthCheck);
}

var form = document.querySelectorAll("form")[0];
if (form) {
    form.addEventListener("submit", function(e) {
        if (!allow_submit) e.preventDefault();
    });
}
