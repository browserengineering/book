function register() {
  let form = document.createElement('form');
  form.innerHTML = 'URL: <input id=urlInput type=text name=url> <input type=submit name=Load>';
  query.appendChild(form);
  form.addEventListener('submit', onFormSubmit);
  urlInput.value = 'http://browser.engineering'
}

function log(str) {
  let div = document.createElement('div');
  div.innerText = str;
  logElement.appendChild(div)
  logElement.scrollTop = logElement.scrollHeight
}

function onFormSubmit(event) {
  event.preventDefault();
  let formData = new FormData(event.target);
  let url = formData.get('url');
  fetch(`http://localhost:8001/proxy?${url}`)
    .then(response => response.text())
    .then(text => {
    	rawContents.textContent = text
    	process(text)
    });
}
