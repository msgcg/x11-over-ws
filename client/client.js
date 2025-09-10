const LOG = (s)=> { document.getElementById('log').textContent += s + "\n"; };
const ws = new WebSocket("ws://" + location.hostname + ":8080/display/99");
ws.binaryType = "arraybuffer";
ws.onopen = ()=> LOG("WS open");
ws.onmessage = (ev)=>{
  if (typeof ev.data === "string") {
    try {
      const obj = JSON.parse(ev.data);
      LOG("CTRL: " + JSON.stringify(obj));
    } catch(e){ LOG("TEXT: " + ev.data); }
  } else {
    const buf = new Uint8Array(ev.data);
    if (buf.length < 4) { LOG("BIN <4"); return; }
    const conn = (buf[0]<<24)|(buf[1]<<16)|(buf[2]<<8)|buf[3];
    LOG("DATA conn=" + conn + " len=" + (buf.length-4));
    // payload is buf.slice(4) — pass to X-server implementation
  }
};
ws.onclose = ()=> LOG("WS closed");