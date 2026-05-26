"""
Lightweight TCP sender for Hermes Display — zero dependencies beyond stdlib.
Use from any AI agent (Hermes, Claude Code, OpenClaw, etc.) to control the display.
"""

import socket
import json
import sys
import time

TCP_PORT = 19876
HOST = "127.0.0.1"

STATES = {
    0: "BOOT", 1: "ANALYZING", 2: "PROCESSING", 3: "EXECUTING",
    4: "SUCCESS", 5: "FAILURE", 6: "CRITICAL", 7: "DISPLAY", 8: "IDLE",
}


def send(state, msg="", host=HOST, port=TCP_PORT, timeout=0.5):
    """Send state to display daemon. Returns True on success."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.settimeout(timeout)
        sock.connect((host, port))
        sock.send((json.dumps({"state": state, "msg": msg}) + "\n").encode())
        return True
    except Exception:
        return False
    finally:
        sock.close()


def send_blocking(state, msg="", host=HOST, port=TCP_PORT, timeout=3):
    """Send with retry (3 attempts)."""
    for _ in range(3):
        if send(state, msg, host, port, timeout):
            return True
        time.sleep(0.1)
    return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python sender.py <state> [message] [--host HOST] [--port PORT]")
        print(f"States: {STATES}")
        sys.exit(1)

    state = sys.argv[1]
    msg = ""
    host = HOST
    port = TCP_PORT

    # Parse optional args
    args = sys.argv[2:]
    i = 0
    while i < len(args):
        if args[i] == "--host" and i + 1 < len(args):
            host = args[i + 1]; i += 2
        elif args[i] == "--port" and i + 1 < len(args):
            port = int(args[i + 1]); i += 2
        else:
            msg = " ".join(args[i:]); break

    # Resolve state (number or name)
    try:
        state = int(state)
    except ValueError:
        name_map = {v.lower(): k for k, v in STATES.items()}
        state = name_map.get(state.lower(), 8)

    ok = send(state, msg, host, port)
    name = STATES.get(state, "?")
    print(f"{'OK' if ok else 'FAIL'}: -> {name} {msg}")
