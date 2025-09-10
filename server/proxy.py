#!/usr/bin/env python3
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
from typing import Dict

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

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

    async def ws_handler(self, ws, path):
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

        async with self._lock:
            if self.ws:
                logging.warning("Another WS already attached, closing new one")
                await ws.close()
                return
            self.ws = ws

        logging.info("WS bound to display %d", self.display)
        try:
            async for message in ws:
                # message can be text (control) or bytes (binary data)
                if isinstance(message, str):
                    # control JSON
                    try:
                        obj = json.loads(message)
                        logging.debug("WS control: %s", obj)
                        # currently no commands expected from browser in prototype
                    except Exception:
                        logging.exception("Bad JSON from ws")
                else:
                    # binary -> first 4 bytes conn_id, rest payload
                    if len(message) < 4:
                        logging.warning("Binary frame too short")
                        continue
                    conn_id = struct.unpack("!I", message[:4])[0]
                    payload = message[4:]
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