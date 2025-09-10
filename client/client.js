// client.js

const WS_PROTOCOL = 'wss:';
const WS_URL = `${WS_PROTOCOL}//${window.location.hostname}:display/99`; // Adjust as needed
const logDiv = document.getElementById('log');
const loginForm = document.getElementById('login-form');
const mainContent = document.getElementById('main-content');
const usernameInput = document.getElementById('username');
const passwordInput = document.getElementById('password');
const loginButton = document.getElementById('login-button');
const loginMessage = document.getElementById('login-message');

let ws = null;

function log(message) {
    const p = document.createElement('p');
    p.textContent = message;
    logDiv.appendChild(p);
}

function connectWebSocket() {
    ws = new WebSocket(WS_URL);

    ws.onopen = () => {
        log('WebSocket connected. Sending authentication credentials...');
        const username = usernameInput.value;
        const password = passwordInput.value;
        ws.send(JSON.stringify({ type: 'AUTH', username: username, password: password }));
    };

    ws.onmessage = (event) => {
        if (typeof event.data === 'string') {
            // Control message (JSON)
            try {
                const msg = JSON.parse(event.data);
                if (msg.type === 'AUTH_SUCCESS') {
                    log('Authentication successful!');
                    loginForm.style.display = 'none';
                    mainContent.style.display = 'block';
                } else if (msg.type === 'AUTH_FAILED') {
                    log(`Authentication failed: ${msg.reason}`);
                    loginMessage.textContent = `Ошибка аутентификации: ${msg.reason}`;
                    ws.close(); // Close connection on auth failure
                } else {
                    log(`Control message: ${JSON.stringify(msg)}`);
                }
            } catch (e) {
                log(`Error parsing JSON: ${event.data}`);
            }
        } else {
            // Binary data
            const buffer = event.data;
            const view = new DataView(buffer);
            if (buffer.byteLength >= 9) { // Проверяем минимальный размер фрейма (1 байт флагов + 4 байта conn_id + 4 байта payload_len)
                const flags = view.getUint8(0); // Читаем флаги (1 байт)
                const connId = view.getUint32(1, false); // Читаем conn_id (4 байта, big-endian)
                const payloadLen = view.getUint32(5, false); // Читаем payload_len (4 байта, big-endian)
                
                let payload = new Uint8Array(buffer, 9, payloadLen); // Получаем payload

                const FLAG_COMPRESSED = 1;
                if (flags & FLAG_COMPRESSED) {
                    try {
                        payload = pako.inflate(payload); // Распаковываем, если установлен флаг сжатия
                    } catch (e) {
                        log(`Error decompressing payload: ${e.message}`);
                        return;
                    }
                }
                log(`Binary data for conn_id ${connId}: ${payload.byteLength} bytes (decompressed)`);
                // In a real X-server, you would process the X11 protocol data here
            } else {
                log(`Binary frame too short: ${buffer.byteLength} bytes`);
            }
        }
    };

    ws.onclose = () => {
        log('WebSocket disconnected.');
        if (mainContent.style.display === 'block') {
            // If already authenticated, show login form again on disconnect
            loginForm.style.display = 'block';
            mainContent.style.display = 'none';
            loginMessage.textContent = 'Соединение разорвано. Пожалуйста, войдите снова.';
        }
    };

    ws.onerror = (error) => {
        log(`WebSocket error: ${error.message}`);
        loginMessage.textContent = `Ошибка соединения: ${error.message}`;
    };
}

loginButton.addEventListener('click', () => {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.close(); // Close existing connection if any
    }
    connectWebSocket();
});

// Initial state: show login form
loginForm.style.display = 'block';
mainContent.style.display = 'none';