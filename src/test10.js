var button = document.querySelectorAll("#button")[0]
var test = document.querySelectorAll("#test")[0]
button.addEventListener("click", function() {
    test.innerHTML = "This is a lot of text that is going" +
        " to break over multiple lines, causing this test" +
        " paragraph to change height, which should be a" +
        " problem for our reflow algorithm."
})
