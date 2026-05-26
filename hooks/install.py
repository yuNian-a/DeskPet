"""Auto-install Hermes Display hooks into Hermes Agent source.

Usage:
    python hooks/install.py              # Install
    python hooks/install.py --uninstall   # Restore from .bak
    python hooks/install.py --check       # Check status
"""

import os, sys, shutil, ast


def find_hermes_source():
    candidates = [
        os.path.expanduser("~/.hermes/hermes-agent/agent/conversation_loop.py"),
        os.path.expanduser("~/.hermes/hermes-agent/conversation_loop.py"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return os.path.dirname(c), c
    return None, None


HOOK_MODULE = '''import socket, json, logging, threading
logger = logging.getLogger(__name__)
TCP_PORT = 19876
HOST = "127.0.0.1"
_LOCK = threading.Lock()

def set_display_state(state: int, msg: str = "") -> None:
    try:
        payload = json.dumps({"state": state, "msg": msg}) + "\\n"
    except Exception:
        return
    def _send():
        try:
            with _LOCK:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.3)
                s.connect((HOST, TCP_PORT))
                s.send(payload.encode())
                s.close()
        except Exception:
            pass
    threading.Thread(target=_send, daemon=True).start()
'''


# Each: (anchor_text, before_or_after, code)
IMPLANTS = []

# 1: Before while loop -> ANALYZING
IMPLANTS.append((
    "while (api_call_count < agent.max_iterations",
    "BEFORE",
    "\n    # Hermes Display Hook: entering analysis\n"
    "    try:\n"
    "        from hermes_display_hook import set_display_state\n"
    '        _preview = (user_message[:60] + "...") if len(user_message) > 60 else user_message\n'
    "        set_display_state(1, _preview)\n"
    "    except Exception:\n"
    "        pass\n\n"
))

# 2: Each loop iteration -> ANALYZING
IMPLANTS.append((
    "api_call_count += 1\n        agent._api_call_count = api_call_count",
    "AFTER",
    "\n        # Hermes Display Hook: thinking (LLM call)\n"
    "        if api_call_count > 1:\n"
    "            try:\n"
    "                from hermes_display_hook import set_display_state\n"
    '                set_display_state(1, f"Thinking... (call #{api_call_count})")\n'
    "            except Exception:\n"
    "                pass\n\n"
))

# 3: Before _execute_tool_calls -> Smart routing
IMPLANTS.append((
    "agent._execute_tool_calls(assistant_message",
    "BEFORE",
    "\n                # Hermes Display Hook: smart state by tool type\n"
    "                try:\n"
    "                    from hermes_display_hook import set_display_state\n"
    "                    _names = [tc.function.name for tc in assistant_message.tool_calls]\n"
    '                    _interactive = {"clarify"}\n'
    '                    _exec = {"terminal", "delegate_task", "execute_code"}\n'
    '                    _proc = {"search_files", "web_search", "read_file", "write_file", "patch"}\n'
    "                    if _interactive & set(_names):\n"
    '                        set_display_state(7, "Awaiting your response...")\n'
    "                    elif _exec & set(_names):\n"
    '                        set_display_state(3, ", ".join(_names[:3]))\n'
    "                    elif _proc & set(_names):\n"
    '                        set_display_state(2, ", ".join(_names[:3]))\n'
    "                    else:\n"
    '                        set_display_state(3, ", ".join(_names[:3]))\n'
    "                except Exception:\n"
    "                    pass\n\n"
))

# 4: Before return result -> SUCCESS/FAILURE/IDLE
IMPLANTS.append((
    "return result",
    "BEFORE",
    "\n    # Hermes Display Hook: turn complete\n"
    "    try:\n"
    "        from hermes_display_hook import set_display_state\n"
    "        if completed and not interrupted and not failed:\n"
    '            set_display_state(8, "")\n'
    "        elif interrupted:\n"
    '            set_display_state(8, "")\n'
    "        elif failed:\n"
    '            set_display_state(5, "Task failed")\n'
    "        else:\n"
    '            set_display_state(8, "")\n'
    "    except Exception:\n"
    "        pass\n\n"
))

# 5: No tool calls -> final response -> SUCCESS
IMPLANTS.append((
    "else:\n                # No tool calls - this is the final response",
    "AFTER",
    "\n                # Hermes Display Hook: final response (no more tool calls)\n"
    "                try:\n"
    "                    from hermes_display_hook import set_display_state\n"
    '                    set_display_state(4, "Task completed")\n'
    "                except Exception:\n"
    "                    pass\n"
))


def install():
    src_dir, target_file = find_hermes_source()
    if not target_file:
        print("ERROR: Cannot find hermes-agent conversation_loop.py")
        sys.exit(1)

    hook_dest = os.path.join(src_dir, "hermes_display_hook.py")
    with open(hook_dest, 'w') as f:
        f.write(HOOK_MODULE)
    print(f"Hook module: {hook_dest}")

    bak = target_file + ".bak"
    if not os.path.exists(bak):
        shutil.copy2(target_file, bak)
        print(f"Backup: {bak}")

    with open(target_file, 'r') as f:
        content = f.read()

    if content.count("hermes_display_hook") >= 4:
        print("Hooks already present. Skipping.")
        return

    modified = content
    for i, (anchor, pos, code) in enumerate(IMPLANTS, 1):
        idx = modified.find(anchor)
        if idx < 0:
            print(f"  [{i}] NOT FOUND: {anchor[:50]}...")
            continue
        if pos == "BEFORE":
            modified = modified[:idx] + code + modified[idx:]
        else:
            end = idx + len(anchor)
            modified = modified[:end] + code + modified[end:]
        print(f"  [{i}] OK")

    try:
        ast.parse(modified)
    except SyntaxError as e:
        print(f"SYNTAX ERROR: {e}")
        shutil.copy2(bak, target_file)
        sys.exit(1)

    with open(target_file, 'w') as f:
        f.write(modified)
    print(f"Done: {target_file}")


def uninstall():
    _, tf = find_hermes_source()
    if not tf: return
    bak = tf + ".bak"
    if os.path.exists(bak):
        shutil.copy2(bak, tf)
        print(f"Restored: {tf}")
    h = os.path.join(os.path.dirname(tf), "hermes_display_hook.py")
    if os.path.exists(h): os.remove(h)


def check():
    _, tf = find_hermes_source()
    if not tf:
        print("Not found")
        return
    with open(tf) as f:
        c = f.read().count("hermes_display_hook")
    print(f"Hooks: {c}/4")


if __name__ == "__main__":
    if "--uninstall" in sys.argv:
        uninstall()
    elif "--check" in sys.argv:
        check()
    else:
        install()
