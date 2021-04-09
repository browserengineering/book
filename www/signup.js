function SignupForm(elt) {
    if (window.localStorage["signup"] === "close") return elt.remove();

    this.form = elt;
    this.$initial = elt.querySelector(".s-initial");
    this.$progress = elt.querySelector(".s-progress");
    this.$success = elt.querySelector(".s-success");
    this.$error = elt.querySelector(".s-error");
    this.$close = elt.querySelector("#signup-close");
    this.initial_class = this.form.className;

    this.state = "s-initial";
    this.form.classList.add("s-initial")

    var that = this;
    this.form.addEventListener("submit", function(evt) { that.submit(evt); });
    this.form.addEventListener("reset", function(evt) { that.reset(evt); });
    this.$close.addEventListener("click", function(evt) { that.close(evt); });

    if (window.localStorage["signup"] === "done") {
        this.handle_response({
            "result": "success",
            "msg": "Thanks for signing up for emails!"
        })
    }
}

SignupForm.prototype.change_state = function(state) {
    this.form.classList.replace(this.state, state);
    this.state = state;
}

SignupForm.prototype.submit = function (evt) {
    this.change_state("s-progress");
    var url = this.form.getAttribute("action").replace("/post?", "/post-json?");

    var that = this;
    window.jsonp_response_handler = function(arg) { that.handle_response(arg); };
    url += "&c=jsonp_response_handler";

    var name = this.form.querySelector("#signup-name").value;
    var email = this.form.querySelector("#signup-email").value;
    var type = this.form.querySelector("#signup-emailtype").checked;
    
    url += "&NAME=" + encodeURIComponent(name);
    url += "&EMAIL=" + encodeURIComponent(email);
    url += "&EMAILTYPE=" + (type ? "text" : "html");

    var $script = document.createElement("script");
    $script.async = true;
    $script.src = url;
    $script.onerror = function (evt) {
        that.handle_response({ "result": "error", "msg": evt.message });
    };
    document.querySelector("head").appendChild($script);

    evt.preventDefault();
}

SignupForm.prototype.reset = function(evt) {
    this.form.reset();
    this.change_state("s-initial");
}

SignupForm.prototype.close = function(evt) {
    window.localStorage["signup"] = "close";
    this.form.remove();
}

SignupForm.prototype.handle_response = function(arg) {
    if (!arg.result) arg.result = "error";
    if (!arg.msg) arg.msg = "Error: " + JSON.stringify(arg);

    if (arg.result === "error") {
        this.change_state("s-error");
        var msg = arg.msg;
        if (msg.indexOf(" - ") >= 0) msg = msg.split(" - ", 2)[1];
        this.$error.innerHTML = msg;
        var button = document.createElement("button");
        button.type = "reset";
        button.textContent = "Try again";
        this.$error.appendChild(button);
    } else if (arg.result === "success") {
        this.change_state("s-success");
        this.$success.innerHTML = arg.msg;
        window.localStorage["signup"] = "done";
    }
}

var form = document.getElementById("signup");
new SignupForm(form);
