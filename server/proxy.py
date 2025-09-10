"""
proxy.py
TCP (X11 clients) <-> WebSocket (browser X-server) multiplexer.
Usage example:
  python3 proxy.py --display 99 --ws-host 0.0.0.0 --ws-port 8080 --tcp-host 0.0.0.0
This will listen TCP on port 6000 + display (e.g. 6099) and WS on ws-port.
"""
import asyncio
import websockets
import argparse
import json
import struct
import itertools
import logging
import zlib
from typing import Dict
import pam # Добавляем импорт pam
import ssl

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")

class DisplayProxy:
    def __init__(self, display: int, ws_host: str, ws_port: int, tcp_host: str):
        self.display = display
        self.ws_host = ws_host
        self.ws_port = ws_port
        self.tcp_host = tcp_host
        self.tcp_port = 6000 + display
        self.ws = None  # active websocket for this display (one browser)
        self.next_conn = itertools.count(1)
        self.conns: Dict[int, asyncio.StreamWriter] = {}  # conn_id -> tcp writer
        self._lock = asyncio.Lock()

        self.ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        self.ssl_context.load_cert_chain('server/certs/fullchain1.pem', 'server/certs/privkey1.pem')

    async def start(self):
        logging.info(f"Starting WebSocket server on wss://{self.ws_host}:{self.ws_port}")
        start_server = websockets.serve(
            self.ws_handler,
            self.ws_host,
            self.ws_port,
            ssl=self.ssl_context,
            max_size=None,
            max_queue=None
        )
        await start_server

        logging.info(f"Starting TCP server on tcp://{self.tcp_host}:{self.tcp_port}")
        tcp_srv = await asyncio.start_server(
            self.tcp_client_handler,
            self.tcp_host,
            self.tcp_port
        )
        async with tcp_srv:
            await asyncio.Future()  # run forever

    async def ws_handler(self, ws: websockets.WebSocketServerProtocol) -> None:
            # --- НАЧАЛО ДИАГНОСТИЧЕСКОГО БЛОКА ---
            logging.info("Handler called with object of type: %s", type(ws))
            #logging.info("Attributes of ws object: %s", dir(ws)) # Можно закомментировать или удалить
            # --- КОНЕЦ ДИАГНОСТИЧЕСКОГО БЛОКА ---

            # ИСПРАВЛЕНО: Получаем путь из объекта request, как доказывают логи
            path = ws.request.path
            logging.info("WS connected for path=%s", path)
            
            # simple path check: /display/99 or /99
            try:
                disp = int(path.strip("/").split("/")[-1])
            except Exception:
                logging.warning("Invalid path %s, closing", path)
                await ws.close()
                return
                
            if disp != self.display:
                logging.warning("WS for wrong display %d != %d", disp, self.display)
                await ws.close()
                return

            # Аутентификация
            try:
                auth_message = await asyncio.wait_for(ws.recv(), timeout=5.0)
                auth_data = json.loads(auth_message)
                username = auth_data.get("username")
                password = auth_data.get("password")

                if not username or not password:
                    logging.warning("Missing username or password in authentication message.")
                    await ws.send(json.dumps({"type": "AUTH_FAILED", "reason": "Missing credentials"}))
                    await ws.close()
                    return

                if not self.authenticate_pam(username, password):
                    logging.warning("PAM authentication failed for user: %s", username)
                    await ws.send(json.dumps({"type": "AUTH_FAILED", "reason": "Invalid credentials"}))
                    await ws.close()
                    return
                logging.info("PAM authentication successful for user: %s", username)
                await ws.send(json.dumps({"type": "AUTH_SUCCESS"}))

            except asyncio.TimeoutError:
                logging.warning("Authentication timeout, closing connection.")
                await ws.close()
                return
            except json.JSONDecodeError:
                logging.warning("Invalid JSON in authentication message.")
                await ws.close()
                return
            except Exception as e:
                logging.exception("Error during authentication: %s", e)
                await ws.close()
                return

            async with self._lock:
                if self.ws:
                    logging.warning("Another WS already attached, closing new one")
                    await ws.close()
                    return
                self.ws = ws

            logging.info("WS bound to display %d", self.display)
            try:
                async for message in ws:
                    if isinstance(message, str):
                        try:
                            obj = json.loads(message)
                            logging.debug("WS control: %s", obj)
                        except Exception:
                            logging.exception("Bad JSON from ws")
                    else:
                        if len(message) < 9:
                            logging.warning("Binary frame too short")
                            continue
                        flags = message[0]
                        conn_id = struct.unpack("!I", message[1:5])[0]
                        payload_len = struct.unpack("!I", message[5:9])[0]
                        payload = message[9:9+payload_len]

                        if flags & 1:
                            try:
                                payload = zlib.decompress(payload)
                            except zlib.error as e:
                                logging.error("Decompression error: %s", e)
                                continue

                        writer = self.conns.get(conn_id)
                        if writer:
                            writer.write(payload)
                            await writer.drain()
                        else:
                            logging.warning("No TCP writer for conn %d", conn_id)
            except websockets.exceptions.ConnectionClosed:
                logging.info("WS disconnected")
            finally:
                # cleanup on ws close: close all tcp connections
                async with self._lock:
                    self.ws = None
                    conns = list(self.conns.items())
                    self.conns.clear()
                for cid, w in conns:
                    try:
                        w.close()
                        await w.wait_closed()
                    except Exception:
                        pass
                logging.info("Cleaned up %d connections", len(conns))

    def authenticate_pam(self, username, password):
        p = pam.pam()
        return p.authenticate(username, password, service='login')

    async def tcp_client_handler(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        addr = writer.get_extra_info('peername')
        logging.info("TCP client connected from %s", addr)
        # Wait until WS is connected
        wait_tries = 0
        while self.ws is None:
            if wait_tries > 600:
                logging.error("No WS connected for display %d, closing TCP client", self.display)
                writer.close()
                await writer.wait_closed()
                return
            await asyncio.sleep(0.1)
            wait_tries += 1

        conn_id = next(self.next_conn)
        self.conns[conn_id] = writer
        logging.info("Assigned conn_id=%d", conn_id)
        # inform browser about new conn
        try:
            await self.ws.send(json.dumps({"type": "NEW_CONN", "conn": conn_id}))
        except Exception:
            logging.exception("Failed to notify WS about new conn")
            # cleanup
            del self.conns[conn_id]
            writer.close()
            await writer.wait_closed()
            return

        try:
            while True:
                data = await reader.read(4096)
                if not data:
                    break
                
                flags = 0
                payload = data
                if len(data) > 64: # Compress if payload is larger than 64 bytes
                    payload = zlib.compress(data)
                    flags |= 1 # Set compression flag

                frame = struct.pack("!BII", flags, conn_id, len(payload)) + payload
                try:
                    await self.ws.send(frame)
                except Exception:
                    logging.exception("Failed to send frame to WS")
                    break
        except Exception:
            logging.exception("Error in tcp read loop")
        finally:
            logging.info("TCP client conn %d closed", conn_id)
            # notify browser
            try:
                if self.ws:
                    await self.ws.send(json.dumps({"type": "CLOSE_CONN", "conn": conn_id}))
            except Exception:
                pass
            # cleanup
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
            self.conns.pop(conn_id, None)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--display", type=int, default=99)
    p.add_argument("--ws-host", default="0.0.0.0")
    p.add_argument("--ws-port", type=int, default=8080)
    p.add_argument("--tcp-host", default="0.0.0.0")
    args = p.parse_args()

    proxy = DisplayProxy(display=args.display, ws_host=args.ws_host, ws_port=args.ws_port, tcp_host=args.tcp_host)
    try:
        asyncio.run(proxy.start())
    except KeyboardInterrupt:
        logging.info("Terminated")

if __name__ == "__main__":
    main()