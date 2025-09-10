// client.js

const WS_URL = `ws://${window.location.hostname}:8080/display/99`; // Adjust as needed
const logDiv = document.getElementById('log');

function log(message) {
    const p = document.createElement('p');
    p.textContent = message;
    logDiv.appendChild(p);
}

const ws = new WebSocket(WS_URL);

ws.onopen = () => {
    log('WebSocket connected.');
};

ws.onmessage = (event) => {
    if (typeof event.data === 'string') {
        // Control message (JSON)
        try {
            const msg = JSON.parse(event.data);
            log(`Control message: ${JSON.stringify(msg)}`);
        } catch (e) {
            log(`Error parsing JSON: ${event.data}`);
        }
    } else {
        // Binary data
        const buffer = event.data;
        const view = new DataView(buffer);
        if (buffer.byteLength >= 4) {
            const connId = view.getUint32(0, false); // big-endian
            const payload = new Uint8Array(buffer, 4);
            log(`Binary data for conn_id ${connId}: ${payload.byteLength} bytes`);
            // In a real X-server, you would process the X11 protocol data here
        } else {
            log(`Binary frame too short: ${buffer.byteLength} bytes`);
        }
    }
};

ws.onclose = () => {
    log('WebSocket disconnected.');
};

ws.onerror = (error) => {
    log(`WebSocket error: ${error.message}`);
};

// Example: sending a PING control message every 30 seconds
setInterval(() => {
    if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'PING' }));
        log('Sent PING.');
    }
}, 30000);