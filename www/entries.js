
function bad_request() {
    if (this.status === 200) return;
    console.error("Something went wrong with the XHR!");
}

function feedback_mode() {
    var elts = document.querySelectorAll("button");
    for (var i = 0; i < elts.length; i++) {
        elts[i].addEventListener('click', function() {
            submit_status(parseInt(this.parentNode.dataset.id), this.className);
            this.parentNode.remove();
        });
    }
}

function submit_status(id, status) {
    var xhr = new XMLHttpRequest();
    xhr.addEventListener("load", bad_request);
    xhr.open("POST", "/api/status");
    xhr.send(JSON.stringify({'id': id, 'status': status}));
}

document.addEventListener("DOMContentLoaded", function() {
    feedback_mode();
});
