import { http_textarea, lib } from "./rt-module.js";

export { socket, tkinter };

const socket = lib.socket({ "http://input/": http_textarea(document.querySelector("#input")) });
const tkinter = lib.tkinter({ canvas: document.querySelector("#canvas"), zoom: 2.0 });
