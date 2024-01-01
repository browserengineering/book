dukpy = {}
$$COMMARRAY = null;
$$READARRAY = null;
$$FLAGARRAY = null;
$$CONSOLE = console;
$$POSTMESSAGE = postMessage;

$$SCOPE = {};

addEventListener("message", (e) => {
    switch (e.data.type) {
    case "eval":
        dukpy = e.data.bindings;
        let val;
        try {
            val = eval?.(e.data.body);
        } catch (e) {
            console.log('Script crashed');
        }
        if (val instanceof Function || val instanceof Object) val = null;
        $$POSTMESSAGE({"type": "return", "data": val});
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
    $$POSTMESSAGE({
        "type": "call",
        "fn": fn,
        "args": args,
    });
    Atomics.wait($$FLAGARRAY, 0, 0);
    let len = $$FLAGARRAY[0];
    Atomics.store($$FLAGARRAY, 0, 0);
    if (len > 0) {
        let buffer = new Uint8Array(len);
        for (let i = 0; i < buffer.length; i++) {
            buffer[i] = $$READARRAY[i];
        }
        let result = JSON.parse(new TextDecoder().decode(buffer));
        return result;
    }
}
