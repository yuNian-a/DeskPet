#!/usr/bin/env python3
"""
Hermes Display Hook — unified handler for Cursor and Claude Code.

Reads hook event JSON from stdin, sends TCP state updates to the display daemon.
Non-blocking, fails silently. Exit 0 with no output (side-effect only).

Install:  python hooks/install_agents.py
"""

import json
import socket
import sys
import threading

TCP_PORT = 19876
HOST = "127.0.0.1"
_SEND_LOCK = threading.Lock()

# Tool names normalized to lowercase for routing
_EXEC_TOOLS = {"shell", "bash", "task", "mcp"}
_PROC_TOOLS = {
    "read", "write", "edit", "grep", "glob",
    "webfetch", "websearch", "search_files", "read_file",
    "write_file", "patch", "str_replace", "create_file",
    "replace_string_in_file", "edit_files", "semsearch",
}
_INTERACTIVE_TOOLS = {"askuserquestion", "clarify"}


def _send(state: int, msg: str = "") -> None:
    try:
        payload = json.dumps({"state": state, "msg": msg}) + "\n"
    except Exception:
        return

    def _do_send():
        try:
            with _SEND_LOCK:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.3)
                sock.connect((HOST, TCP_PORT))
                sock.send(payload.encode())
                sock.close()
        except Exception:
            pass

    threading.Thread(target=_do_send, daemon=True).start()


def _normalize_event(name: str) -> str:
    key = (name or "").lower().replace("_", "")
    aliases = {
        "beforesubmitprompt": "userpromptsubmit",
        "sessionstart": "sessionstart",
        "sessionend": "sessionend",
        "pretooluse": "pretooluse",
        "posttooluse": "posttooluse",
        "posttoolusefailure": "posttoolusefailure",
        "permissionrequest": "permissionrequest",
        "stop": "stop",
        "stopfailure": "stopfailure",
        "subagentstart": "subagentstart",
        "subagentstop": "subagentstop",
    }
    return aliases.get(key, key)


def _tool_label(data: dict) -> str:
    name = data.get("tool_name") or ""
    tool_input = data.get("tool_input") or {}

    if name.lower() in ("shell", "bash"):
        cmd = tool_input.get("command", "")
        return cmd[:60] if cmd else name
    if name.lower() == "task":
        prompt = tool_input.get("prompt", "")
        return prompt[:60] if prompt else "Task"
    if name.lower() in ("write", "edit"):
        path = tool_input.get("file_path") or tool_input.get("path", "")
        return path.split("/")[-1][:40] if path else name
    return name


def _route_tool(data: dict) -> None:
    raw = (data.get("tool_name") or "").lower()
    # Strip MCP prefix: "mcp:server:tool" -> treat as exec
    base = raw.split(":")[-1] if ":" in raw else raw
    label = _tool_label(data)

    if base in _INTERACTIVE_TOOLS or raw.startswith("ask"):
        _send(7, "Awaiting your response...")
    elif base in _EXEC_TOOLS or raw.startswith("mcp"):
        _send(3, label)
    elif base in _PROC_TOOLS:
        _send(2, label)
    else:
        _send(3, label)


def handle(data: dict) -> None:
    event = _normalize_event(data.get("hook_event_name", ""))

    if event == "sessionstart":
        _send(0, "Starting session...")
        return

    if event == "userpromptsubmit":
        prompt = data.get("prompt", "")
        preview = (prompt[:60] + "...") if len(prompt) > 60 else prompt
        _send(1, preview or "Analyzing...")
        return

    if event == "pretooluse":
        _route_tool(data)
        return

    if event == "permissionrequest":
        _send(7, "Awaiting permission...")
        return

    if event == "posttoolusefailure":
        err = data.get("error") or data.get("reason") or "Tool failed"
        _send(5, str(err)[:60])
        return

    if event == "stop":
        status = (data.get("status") or "").lower()
        if status == "error":
            _send(5, "Agent error")
        elif status == "aborted":
            _send(8, "")
        else:
            _send(4, "Task completed")
            _send(8, "")
        return

    if event == "stopfailure":
        err = data.get("error") or data.get("last_assistant_message") or "API error"
        _send(6, str(err)[:60])
        return

    if event == "sessionend":
        _send(8, "")
        return

    if event == "subagentstart":
        agent = data.get("agent_type") or data.get("subagent_type") or "subagent"
        _send(2, f"Subagent: {agent}")
        return

    if event == "subagentstop":
        _send(1, "Subagent done")
        return


def main() -> None:
    raw = sys.stdin.read()
    if not raw.strip():
        sys.exit(0)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        sys.exit(0)
    try:
        handle(data)
    except Exception:
        pass
    sys.exit(0)


if __name__ == "__main__":
    main()
