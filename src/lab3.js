class Text {
  constructor(text) {
  	this.text = text;
  }
}

class Tag {
  constructor(tag) {
  	this.tag = tag
  }
}

async function lex(body) {
    let text = ""
    let in_angle = false
    for (let c of body) {
        if (c == "<")
            in_angle = true
        else if (c == ">")
            in_angle = false
        else if (!in_angle)
            text += c
        await potentialBreakpointLex(text);
    }
    return text
}

let [WIDTH, HEIGHT] = [800, 600]
let [HSTEP, VSTEP] = [6, 18]

let SCROLL_STEP = 100

class Font {
  constructor(size, weight, font) {
  	this.size = size;
  	this.weight = weight;
  	this.font = font;
  }

  measure() {
  	let span = document.createElement();
  	document.body.appendChild(span);
  	span.style.font = style;
  	span.style.fontSize = this.size;
  	span.style.height = 'auto';
  	span.style.width = 'auto';
  	span.style.position = 'absolute';
  	span.style.whiteSpace = 'no-wrap';
  	let width = Math.ceil(text.clientWidth);
  	document.body.removeChild(span);
  	return width;
  }
}

class Layout {
  constructor(tokens) {
  	this.tokens = tokens
  	this.display_list = []
  	this.cursor_x = HSTEP
  	this.cursor_y = VSTEP
  	this.weight = "normal"
  	this.style = "times new roman"
  	this.size = 16
    this.line = []
    for (let tok of tokens)
      this.token(tok)
    this.flush
  }

  token(tok) {
    if (tok instanceof Text)
      text(tok.text)
    else if (tok.tag == "i")
      this.style = "italic"
    else if (tok.tag == "/i")
      this.style = "roman"
    else if (tok.tag == "b")
      this.weight = "bold"
    else if (tok.tag == "/b")
      this.weight = "normal"
    else if (tok.tag == "small")
      this.size -= 2
    else if (tok.tag == "/small")
      this.size += 2
    else if (tok.tag == "big")
      this.size += 4
    else if (tok.tag == "/big")
      this.size -= 4
    else if (tok.tag == "br")
      this.flush()
    else if (tok.tag == "/p") {
      this.flush()
      this.cursor_y += VSTEP
    }
  }

  text(text) {
  	let font = new Font(
  		this.size,
  		this.weight,
  		this.style);
  	for (let word of text.split()) {
  	  let w = font.measure();
  	  if (this.cursor_x + w > WIDTH - HSTEP)
  		this.flush();
  	  let cursor_x = this.cursor_x
      this.line.push({cursor_x, word, font});
  	  this.cursor_x += w + font.measure(" ")
  	}
  }

  flush() {
  	if (!this.line)
  	  return;
  	// There is no JS API (yet) for font metrics
  	let ascent = 10
  	let max_ascent = 10
  	let baseline = this.cursor_y + 1.2 * max_ascent
  	for (let {x, word, font} of this.line) {
  	  let y = baseline - ascent;
  	  this.display_list.push({x, y, word, font})
  	}
  	this.cursor_x = HSTEP
  	this.line = []
  	// See comment above
  	let max_descent = 6
  	this.cursor_y = baseline + 1.2 * max_descent
  }
}

class Browser {
  constructor(canvasElement) {
    this.canvasElement = canvasElement;
    this.canvasContext = canvasElement.getContext('2d');

    this.scroll = 0
  }

  async load(body) {
    let tokens = await lex(body);
    this.display_list = new Layout(tokens).display_list;
    await this.render();
  }

  async render() {
    let count = 0;
    this.canvasContext.clearRect(0, 0, this.canvasElement.width,
       this.canvasElement.height);
    this.canvasContext.font = '16px serif';
    for (let entry of this.display_list) {
      let {x, y, word, font} = entry;
      if (y > this.scroll + HEIGHT)
        continue;
      if (y + VSTEP < this.scroll)
        continue;
      this.canvasContext.fillText(c, x, y - this.scroll);
      await potentialBreakpointRender(count++);
    }
  }

  scrolldown() {
    this.scroll += SCROLL_STEP;
    this.render()
  }
}