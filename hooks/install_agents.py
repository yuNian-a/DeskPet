"""Install Hermes Display hooks for Cursor and Claude Code.

Usage:
    python hooks/install_agents.py              # Install to user home (~/.cursor, ~/.claude)
    python hooks/install_agents.py --project    # Install to current project (.cursor, .claude)
    python hooks/install_agents.py --cursor     # Cursor only
    python hooks/install_agents.py --claude     # Claude Code only
    python hooks/install_agents.py --check      # Check installation status
    python hooks/install_agents.py --uninstall  # Remove user-level hooks
"""

import json
import os
import shutil
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
HOOK_SCRIPT = os.path.join(SCRIPT_DIR, "display_hook.py")

CURSOR_HOOKS_JSON = {
    "version": 1,
    "hooks": {
        "sessionStart": [{"command": "python ./hooks/display_hook.py"}],
        "beforeSubmitPrompt": [{"command": "python ./hooks/display_hook.py"}],
        "preToolUse": [{"command": "python ./hooks/display_hook.py"}],
        "stop": [{"command": "python ./hooks/display_hook.py"}],
        "sessionEnd": [{"command": "python ./hooks/display_hook.py"}],
        "postToolUseFailure": [{"command": "python ./hooks/display_hook.py"}],
    },
}

CLAUDE_HOOK_CMD = {
    "type": "command",
    "command": "python ./hooks/display_hook.py",
    "timeout": 5,
}

CLAUDE_EVENTS = [
    "SessionStart",
    "UserPromptSubmit",
    "PreToolUse",
    "PermissionRequest",
    "Stop",
    "StopFailure",
    "SessionEnd",
    "PostToolUseFailure",
]


def _merge_claude_settings(existing: dict) -> dict:
    hooks = existing.setdefault("hooks", {})
    display_group = [{"hooks": [CLAUDE_HOOK_CMD]}]
    for event in CLAUDE_EVENTS:
        groups = hooks.setdefault(event, [])
        if not any(
            g.get("hooks", [{}])[0].get("command", "").endswith("display_hook.py")
            for g in groups
            if g.get("hooks")
        ):
            groups.append(display_group[0])
    return existing


def _install_cursor(target_dir: str) -> None:
    hooks_dir = os.path.join(target_dir, "hooks")
    os.makedirs(hooks_dir, exist_ok=True)
    shutil.copy2(HOOK_SCRIPT, os.path.join(hooks_dir, "display_hook.py"))

    hooks_json_path = os.path.join(target_dir, "hooks.json")
    if target_dir.endswith(".cursor") and not target_dir.startswith(PROJECT_ROOT):
        # User-level: use ./hooks/ relative path
        with open(hooks_json_path, "w", encoding="utf-8") as f:
            json.dump(CURSOR_HOOKS_JSON, f, indent=2)
            f.write("\n")
    else:
        # Project-level: copy template from repo
        template = os.path.join(PROJECT_ROOT, ".cursor", "hooks.json")
        if os.path.exists(template):
            shutil.copy2(template, hooks_json_path)
        else:
            with open(hooks_json_path, "w", encoding="utf-8") as f:
                json.dump(CURSOR_HOOKS_JSON, f, indent=2)
                f.write("\n")
        shutil.copy2(HOOK_SCRIPT, os.path.join(hooks_dir, "display_hook.py"))

    print(f"  Cursor: {hooks_json_path}")


def _install_claude(target_dir: str) -> None:
    hooks_dir = os.path.join(target_dir, "hooks")
    os.makedirs(hooks_dir, exist_ok=True)
    shutil.copy2(HOOK_SCRIPT, os.path.join(hooks_dir, "display_hook.py"))

    settings_path = os.path.join(target_dir, "settings.json")
    existing = {}
    if os.path.exists(settings_path):
        with open(settings_path, encoding="utf-8") as f:
            existing = json.load(f)

    merged = _merge_claude_settings(existing)
    with open(settings_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2)
        f.write("\n")

    print(f"  Claude Code: {settings_path}")


def install(project: bool = False, cursor: bool = True, claude: bool = True) -> None:
    if project:
        if cursor:
            _install_cursor(os.path.join(PROJECT_ROOT, ".cursor"))
        if claude:
            _install_claude(os.path.join(PROJECT_ROOT, ".claude"))
    else:
        home = os.path.expanduser("~")
        if cursor:
            _install_cursor(os.path.join(home, ".cursor"))
        if claude:
            _install_claude(os.path.join(home, ".claude"))


def uninstall() -> None:
    home = os.path.expanduser("~")
    hook_file = os.path.join(home, ".cursor", "hooks", "display_hook.py")
    if os.path.exists(hook_file):
        os.remove(hook_file)
        print(f"  Removed: {hook_file}")

    claude_hook = os.path.join(home, ".claude", "hooks", "display_hook.py")
    if os.path.exists(claude_hook):
        os.remove(claude_hook)
        print(f"  Removed: {claude_hook}")

    for settings_path in [
        os.path.join(home, ".claude", "settings.json"),
    ]:
        if not os.path.exists(settings_path):
            continue
        with open(settings_path, encoding="utf-8") as f:
            data = json.load(f)
        hooks = data.get("hooks", {})
        for event in CLAUDE_EVENTS:
            if event not in hooks:
                continue
            hooks[event] = [
                g for g in hooks[event]
                if not any(
                    h.get("command", "").endswith("display_hook.py")
                    for h in g.get("hooks", [])
                )
            ]
            if not hooks[event]:
                del hooks[event]
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
        print(f"  Cleaned: {settings_path}")

    print("Uninstall done. Remove ~/.cursor/hooks.json manually if needed.")


def check() -> None:
    home = os.path.expanduser("~")
    cursor_hook = os.path.join(home, ".cursor", "hooks", "display_hook.py")
    cursor_json = os.path.join(home, ".cursor", "hooks.json")
    claude_hook = os.path.join(home, ".claude", "hooks", "display_hook.py")
    claude_settings = os.path.join(home, ".claude", "settings.json")

    print("Cursor:")
    print(f"  hook script: {'OK' if os.path.exists(cursor_hook) else 'MISSING'}")
    print(f"  hooks.json:  {'OK' if os.path.exists(cursor_json) else 'MISSING'}")

    print("Claude Code:")
    print(f"  hook script: {'OK' if os.path.exists(claude_hook) else 'MISSING'}")
    if os.path.exists(claude_settings):
        with open(claude_settings, encoding="utf-8") as f:
            data = json.load(f)
        count = sum(
            1 for event in CLAUDE_EVENTS
            if event in data.get("hooks", {})
        )
        print(f"  settings.json: OK ({count}/{len(CLAUDE_EVENTS)} events)")
    else:
        print("  settings.json: MISSING")

    project_cursor = os.path.join(PROJECT_ROOT, ".cursor", "hooks", "display_hook.py")
    project_claude = os.path.join(PROJECT_ROOT, ".claude", "hooks", "display_hook.py")
    print("Project templates:")
    print(f"  .cursor: {'OK' if os.path.exists(project_cursor) else 'MISSING'}")
    print(f"  .claude: {'OK' if os.path.exists(project_claude) else 'MISSING'}")


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--uninstall" in args:
        uninstall()
    elif "--check" in args:
        check()
    else:
        project = "--project" in args
        cursor = "--claude" not in args or "--cursor" in args
        claude = "--cursor" not in args or "--claude" in args
        if "--cursor" in args and "--claude" not in args:
            claude = False
        if "--claude" in args and "--cursor" not in args:
            cursor = False
        print("Installing Hermes Display hooks...")
        install(project=project, cursor=cursor, claude=claude)
        print("Done. Restart Cursor / Claude Code to load hooks.")
