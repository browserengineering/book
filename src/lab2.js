function lex(body) {
    let text = ""
    let in_angle = false
    for (let c of body) {
        if (c == "<")
            in_angle = true
        else if (c == ">")
            in_angle = false
        else if (!in_angle)
            text += c
    }
    return text
}

let [WIDTH, HEIGHT] = [800, 600]
let [HSTEP, VSTEP] = [6, 18]

let SCROLL_STEP = 100

function layout(text) {
    let display_list = []
    let [x, y] = [HSTEP, VSTEP]
    for (let c of text) {
        display_list.push([x, y, c])
        x += HSTEP
        if (x >= WIDTH - HSTEP) {
            y += VSTEP
            x = HSTEP
        }
    }
    return display_list
}

class Browser {
  constructor(canvasElement) {
    this.canvasElement = canvasElement;
    this.canvasContext = canvasElement.getContext('2d');

    this.scroll = 0
  }

  load(body) {
    let text = lex(body);
    this.display_list = layout(text);
    this.render();
  }

  render() {
    this.canvasContext.clearRect(0, 0, this.canvasElement.width,
       this.canvasElement.height);
    this.canvasContext.font = '12px serif';
    for (let entry of this.display_list) {
      let [x, y, c] = entry;
      if (y > this.scroll + HEIGHT)
        continue;
      if (y + VSTEP < this.scroll)
        continue;
      this.canvasContext.fillText(c, x, y - this.scroll);
    }
  }

  scrolldown() {
    this.scroll += SCROLL_STEP;
    this.render()
  }
}