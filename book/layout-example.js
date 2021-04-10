let preamble = `
	<style>
  * { box-sizing: border-box; margin: 8px; min-height: 16px; }
  html, body, div { border: 3px solid green; background: lightgreen; }
  html { border: none; margin: 0; }
  h1, p { border: 3px solid darkblue; background: lightblue; padding: 8px; min-height: 0; }
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
