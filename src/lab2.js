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
let [HSTEP, VSTEP] = [10, 18]

let SCROLL_STEP = 100

async function layout(text) {
    let display_list = []
    let [x, y] = [HSTEP, VSTEP]
    for (let c of text) {
        display_list.push([x, y, c])
        x += HSTEP
        if (x >= WIDTH - HSTEP) {
            y += VSTEP
            x = HSTEP
        }
        await potentialBreakpointLayout(display_list)
    }
    return display_list
}

class Browser {
  constructor(canvasElement) {
    this.canvasElement = canvasElement;
    const rectangle = canvasElement.getBoundingClientRect();
    canvasElement.width = rectangle.width * devicePixelRatio;
    canvasElement.height = rectangle.height * devicePixelRatio;
    this.canvasContext = canvasElement.getContext('2d');
    this.scroll = 0;
  }

  async load(body) {
    this.clearCanvas();
    let text = await lex(body);
    this.display_list = await layout(text);
    await this.render();
  }

  clearCanvas() {
    this.canvasContext.clearRect(0, 0, this.canvasElement.width,
        this.canvasElement.height);
  }

  async render() {
    let count = 0;
    this.canvasContext.font = "normal normal 16px sans-serif";
    console.log(this.canvasContext.font)
    for (let entry of this.display_list) {
      let [x, y, c] = entry;
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