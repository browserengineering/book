let preamble = `
	<style>
  * {
	box-sizing: border-box;
  }
  body {
  	font-family: 'Lora', 'Times', sans-serif;
	  font-size: 16px;
	  display: block;
    border: 3px solid green;
    background: lightgreen;
    height: 230px;
  }
  html {
    background: lightgreen;
  }
  h1, p {
  	background: lightblue;
  }
</style>
`;
 
function updateState() {
  targetIframe.srcdoc = `${preamble}${htmlSource.value}`;
  link.href =
  	`layout-block-container-example.html?htmlSource=${
  		  encodeURIComponent(htmlSource.value)}`;
}

onload = () => {
	console.log('load');
	let url = new URL(window.location);
	let source = url.searchParams.get("htmlSource");
	if (source)
		htmlSource.value = decodeURIComponent(source);
	if (!url.searchParams.get("embed"))
		caption.style.display = 'none';
	updateState();
  editExample.addEventListener('submit', () => {
    event.preventDefault();
    updateState();
  });
};