"""
Hermes Display Hook — drop-in module for Hermes Agent.
Imported by conversation_loop.py at key state transitions.

Non-blocking (daemon thread), fails silently.
States: 0=BOOT 1=ANALYZING 2=PROCESSING 3=EXECUTING
        4=SUCCESS 5=FAILURE 6=CRITICAL 7=DISPLAY 8=IDLE

Install:  python hooks/install.py
Uninstall: python hooks/install.py --uninstall
"""

import socket
import json
import logging
import threading

logger = logging.getLogger(__name__)

TCP_PORT = 19876
HOST = "127.0.0.1"
_SEND_LOCK = threading.Lock()


def set_display_state(state: int, msg: str = "") -> None:
    """Fire-and-forget state update to the display daemon."""
    try:
        payload = json.dumps({"state": state, "msg": msg}) + "\n"
    except Exception:
        return

    def _send():
        try:
            with _SEND_LOCK:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.3)
                sock.connect((HOST, TCP_PORT))
                sock.send(payload.encode())
                sock.close()
        except Exception:
            pass

    t = threading.Thread(target=_send, daemon=True)
    t.start()
