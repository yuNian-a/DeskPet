#!/usr/bin/env python3
"""
DeskPet Display Hook — Cursor / Claude Code unified handler.

Reads hook event JSON from stdin, sends TCP state updates to the display daemon.
Non-blocking, fails silently. Exit 0 with no output (side-effect only).

States:
  0=BOOT  1=ANALYZING  2=PROCESSING  3=EXECUTING  4=SUCCESS
  5=FAILURE  6=CRITICAL  7=DISPLAY  8=IDLE
  9=THINKING  10=PLANNING  11=SEARCHING  12=ABORTED
"""

import json
import os
import re
import socket
import sys

TCP_PORT = 19876
HOST = "127.0.0.1"

# Debug log (set to None to disable)
_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hook_debug.log")

def _log(msg):
    try:
        with open(_LOG, "a", encoding="utf-8") as f:
            import datetime
            f.write(f"[{datetime.datetime.now()}] {msg}\n")
    except Exception:
        pass


def _send(state: int, msg: str = "") -> None:
    try:
        payload = json.dumps({"state": state, "msg": msg}) + "\n"
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.1)
        sock.connect((HOST, TCP_PORT))
        sock.send(payload.encode())
        sock.close()
    except Exception:
        pass


# ─── 工具分类 ────────────────────────────────────────────────────────────────

# 执行类：Shell / MCP / Task / 浏览器
_EXEC_TOOLS = {"shell", "bash", "task", "mcp", "computer"}

# 搜索/阅读类：读文件、搜索
_SEARCH_TOOLS = {
    "grep", "glob", "semanticsearch", "semsearch", "websearch",
    "read", "read_file", "search_files",
}

# 编辑类：写文件
_EDIT_TOOLS = {
    "write", "edit", "strreplace", "str_replace", "patch",
    "write_file", "create_file", "replace_string_in_file",
    "edit_files", "editnotebook",
}

# 交互类：需要用户回应
_INTERACTIVE_TOOLS = {"askuserquestion", "clarify", "askquestion"}

# 网络类
_WEB_TOOLS = {"webfetch", "fetchmcpresource"}


def _tool_label(data: dict) -> str:
    name = data.get("tool_name") or ""
    tip = data.get("tool_input") or {}
    nl = name.lower()
    if nl in ("shell", "bash"):
        cmd = tip.get("command", "")
        return cmd[:60] if cmd else name
    if nl == "task":
        return (tip.get("description") or tip.get("prompt", ""))[:60] or "Task"
    if nl in ("write", "edit", "strreplace", "str_replace"):
        path = tip.get("file_path") or tip.get("path", "")
        return path.split("/")[-1].split("\\")[-1][:40] if path else name
    if nl in ("grep", "semanticsearch", "semsearch"):
        return (tip.get("pattern") or tip.get("query", ""))[:40] or name
    return name


def _route_tool(data: dict) -> None:
    raw = (data.get("tool_name") or "").lower()
    base = raw.split(":")[-1] if ":" in raw else raw  # strip MCP prefix
    label = _tool_label(data)

    if base in _interactive_lower() or raw.startswith("ask"):
        _send(7, "等你回复...")
    elif base in _exec_lower() or raw.startswith("mcp") or raw.startswith("call"):
        _send(3, label)
    elif base in _search_lower():
        _send(11, label)
    elif base in _edit_lower():
        _send(2, label)
    elif base in _web_lower():
        _send(3, label)
    else:
        _send(3, label)


def _exec_lower():   return {t.lower() for t in _EXEC_TOOLS}
def _search_lower(): return {t.lower() for t in _SEARCH_TOOLS}
def _edit_lower():   return {t.lower() for t in _EDIT_TOOLS}
def _web_lower():    return {t.lower() for t in _WEB_TOOLS}
def _interactive_lower(): return {t.lower() for t in _INTERACTIVE_TOOLS}


# ─── 事件处理 ─────────────────────────────────────────────────────────────────

def _normalize_event(name: str) -> str:
    key = (name or "").lower().replace("_", "")
    return {
        "beforesubmitprompt": "userpromptsubmit",
        "sessionstart":        "sessionstart",
        "sessionend":          "sessionend",
        "pretooluse":          "pretooluse",
        "posttooluse":         "posttooluse",
        "posttoolusefailure":  "posttoolusefailure",
        "permissionrequest":   "permissionrequest",
        "stop":                "stop",
        "stopfailure":         "stopfailure",
        "subagentstart":       "subagentstart",
        "subagentstop":        "subagentstop",
    }.get(key, key)


def handle(data: dict) -> None:
    event = _normalize_event(data.get("hook_event_name", ""))
    model = (data.get("model") or "").lower()
    mode  = (data.get("composer_mode") or "").lower()

    # ── 会话开始
    if event == "sessionstart":
        _send(0, "启动...")
        return

    # ── 用户提交 prompt
    if event == "userpromptsubmit":
        if mode == "plan":
            _send(10, "规划中...")          # Plan 模式 → 看纸
        elif "thinking" in model:
            _send(9, "深度思考中...")        # Thinking 模式 → 思考动作
        else:
            _send(1, "分析中...")            # 普通 → 思考
        return

    # ── 工具调用前
    if event == "pretooluse":
        _route_tool(data)
        return

    # ── 等待权限
    if event == "permissionrequest":
        _send(7, "等待授权...")
        return

    # ── 工具调用后（成功）：短暂回到 thinking
    if event == "posttooluse":
        if "thinking" in model:
            _send(9, "")
        else:
            _send(1, "")
        return

    # ── 工具调用失败
    if event == "posttoolusefailure":
        err = data.get("error") or data.get("reason") or "Tool failed"
        _send(5, str(err)[:60])
        return

    # ── agent 停止
    if event == "stop":
        status = (data.get("status") or "").lower()
        if status == "error":
            _send(5, "出错了")
        elif status == "aborted":
            _send(12, "")               # 被打断 → 摇头
        else:
            _send(4, "完成！")           # 成功 → 得意（2s后自动回idle）
        return

    # ── agent 崩溃
    if event == "stopfailure":
        err = data.get("error") or data.get("last_assistant_message") or "API error"
        _send(6, str(err)[:60])
        return

    # ── 会话结束
    if event == "sessionend":
        _send(8, "")
        return

    # ── 子 agent 启动
    if event == "subagentstart":
        agent = data.get("description") or data.get("subagent_type") or "subagent"
        if "thinking" in model:
            _send(9, f"子任务: {agent[:40]}")
        else:
            _send(11, f"子任务: {agent[:40]}")
        return

    # ── 子 agent 结束
    if event == "subagentstop":
        _send(1, "子任务完成")
        return


# ─── 入口 ─────────────────────────────────────────────────────────────────────

def _safe_parse(raw: str):
    """尝试解析 JSON，对无效 Unicode 转义做容错处理。"""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # 替换掉孤立的 surrogate 转义如 \uD800-\uDFFF
        cleaned = re.sub(r'\\u[dD][89aAbBcCdDeEfF][0-9a-fA-F]{2}', '?', raw)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return None


def main() -> None:
    raw_bytes = sys.stdin.buffer.read()
    if raw_bytes.startswith(b"\xef\xbb\xbf"):
        raw_bytes = raw_bytes[3:]
    raw = raw_bytes.decode("utf-8", errors="replace")

    _log(f"event={repr(raw[50:120])}")

    if not raw.strip():
        sys.exit(0)

    data = _safe_parse(raw)
    if data is None:
        _log("parse failed")
        sys.exit(0)

    try:
        handle(data)
    except Exception as e:
        _log(f"handle error: {e}")

    sys.exit(0)


if __name__ == "__main__":
    main()
