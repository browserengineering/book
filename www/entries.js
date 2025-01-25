
function bad_request() {
    if (this.status === 200) return;
    console.error("Something went wrong with the XHR!");
}

function feedback_mode() {
    var elts = document.querySelectorAll("button");
    for (var i = 0; i < elts.length; i++) {
        elts[i].addEventListener('click', function() {
            var pw = window.localStorage["pw"];
            submit_status(parseInt(this.parentNode.dataset.id), this.className, pw);
            setTimeout(function () { location.reload(); }, 100);
        });
    }
}

function submit_status(id, status, pw) {
    var xhr = new XMLHttpRequest();
    xhr.addEventListener("load", bad_request);
    xhr.open("POST", "/api/status");
    xhr.send(JSON.stringify({'id': id, 'status': status, 'pw': pw}));
}

document.addEventListener("DOMContentLoaded", function() {
    feedback_mode();
});
