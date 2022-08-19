dukpy = {}
$$COMMARRAY = null;
$$READARRAY = null;
$$FLAGARRAY = null;

addEventListener("message", (e) => {
    switch (e.data.type) {
    case "eval":
        dukpy = e.data.bindings;
        let val = eval(e.data.body);
        postMessage({"type": "return", "data": val});
        break;

    case "array":
        $$COMMARRAY = e.data.buffer;
        $$READARRAY = new Int32Array($$COMMARRAY, 4);
        $$FLAGARRAY = new Int32Array($$COMMARRAY, 0, 1);
        break;
    }
});


function call_python() {
    let args = Array.from(arguments);
    let fn = args.shift();
    postMessage({
        "type": "call",
        "fn": fn,
        "args": args,
    });
    Atomics.wait($$FLAGARRAY, 0, 0);
    let len = $$FLAGARRAY[0];
    Atomics.store($$FLAGARRAY, 0, 0);
    let buffer = new Uint8Array(len);
    for (let i = 0; i < buffer.length; i++) {
        buffer[i] = $$READARRAY[i];
    }
    let result = JSON.parse(new TextDecoder().decode(buffer));
    return result;
}
