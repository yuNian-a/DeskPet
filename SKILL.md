---
name: hermes-display
description: "Cartoon cyberpunk robot status display for secondary USB monitors (596x480). 9 animated states via TCP JSON on port 19876. Robot scale 2.0. One-click launcher: hermes command auto-starts display."
version: 1.1.0
author: Parker
platforms: [windows]
tags: [display, monitor, animation, pygame, status, cyberpunk, robot]
---

# Hermes Display

Cartoon cyberpunk robot on a secondary USB monitor that mirrors AI agent state in real time.

## Architecture

```
AI Agent   --TCP JSON:19876-->  Windows pygame (60fps)  -->  Secondary Monitor
(Hermes/Claude/OpenClaw)       9 animated robot states        596x480 @ (0,1440)
```

## Quick Start (new machine)

```batch
D:\workspace\hermes display\install.bat    # Run once: installs everything
```

Then just type `hermes` in WSL — display auto-starts.

## States

| # | Name | Robot |
|---|------|-------|
| 0 | BOOT | Particles converge -> "HERMES" |
| 1 | ANALYZING | Thinking: chin on hand, squinty eyes, "?" orbit, "THINKING..." |
| 2 | PROCESSING | Pipeline: INPUT->PARSE->INFER->OUTPUT nodes |
| 3 | EXECUTING | Working: bouncing, gear spinning, "WORKING..." + progress bar |
| 4 | SUCCESS | Green "OK" + expanding rings + particles |
| 5 | FAILURE | Red "FAIL" + shattering fragments |
| 6 | CRITICAL | Flashing "WARNING" + red alert bars |
| 7 | DISPLAY | Pulsing circle + "WAITING..." (clarify/await user) |
| 8 | IDLE | Lying down, hands behind head, "zZz" floating, "IDLE" |

## Agent Integration

### Hermes (WSL)

Auto-installed by `install.bat`. 5 implant points in `agent/conversation_loop.py`:

| Point | Location | Action |
|-------|----------|--------|
| 1 | Before while loop | -> ANALYZING |
| 2 | Each loop iteration | -> ANALYZING |
| 3 | Before tool execution | Smart routing (clarify->DISPLAY, terminal->EXECUTING, files->PROCESSING) |
| 4 | No tool calls (final) | -> SUCCESS |
| 5 | Before return result | -> IDLE |

Manual install: `python hooks/install.py`

### Cursor

Auto-installed by `install.bat` to `~/.cursor/`. Uses lifecycle hooks:

| Event | Action |
|-------|--------|
| sessionStart | -> BOOT |
| beforeSubmitPrompt | -> ANALYZING |
| preToolUse | Smart tool routing |
| stop | -> SUCCESS -> IDLE |
| sessionEnd | -> IDLE |

Manual install: `python hooks/install_agents.py` or `--project` for repo-level

### Claude Code

Auto-installed by `install.bat` to `~/.claude/settings.json`:

| Event | Action |
|-------|--------|
| SessionStart | -> BOOT |
| UserPromptSubmit | -> ANALYZING |
| PreToolUse | Smart tool routing |
| PermissionRequest | -> DISPLAY |
| Stop | -> SUCCESS -> IDLE |
| StopFailure | -> CRITICAL |

Manual install: `python hooks/install_agents.py`

Check all: `python hooks/install_agents.py --check`
Uninstall: `python hooks/install_agents.py --uninstall`

## Generic Integration

```python
from display.sender import send
send(1, "Analyzing...")
send(4, "Done")
send(8, "")
```

Or TCP: `echo '{"state":1}' | nc 127.0.0.1 19876`

## Customization (display/display.py)

| Variable | Default | Effect |
|----------|---------|--------|
| SCREEN_W, SCREEN_H | 596, 480 | Resolution |
| CORNER_RADIUS | 18 | Rounded corners (0=square) |
| `s = 2.0` in draw_robot() | 2.0 | Robot size |
| TCP_PORT | 19876 | Port |

## Files

```
D:\workspace\hermes display\
├── install.bat               One-click setup
├── hermes_launcher.bat       Manual launcher (if not using WSL auto)
├── stop.bat                  Stop display
├── SKILL.md, README.md
├── display/
│   ├── display.py            Main daemon (pygame, 60fps)
│   ├── sender.py             Lightweight TCP sender
│   ├── start.bat             Windows double-click launcher
│   └── hermes-display-start  WSL auto-start script
├── .cursor/
│   ├── hooks.json            Cursor hooks config (project template)
│   └── hooks/display_hook.py Cursor hook script
├── .claude/
│   ├── settings.json         Claude Code hooks config (project template)
│   └── hooks/display_hook.py Claude Code hook script
├── hooks/
│   ├── display_hook.py       Unified hook for Cursor + Claude Code
│   ├── install_agents.py     Cursor/Claude Code installer
│   ├── hermes_hook.py        Hermes hook module
│   └── install.py            Hermes auto-installer (5 implant points)
└── templates/
    └── claude_code_wrapper.py  Legacy wrapper (use hooks instead)
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Display not on secondary monitor | Check `--pos` matches Windows display layout |
| Taskbar visible | Windows: uncheck "Show taskbar on all displays" |
| TUI input broken after hermes start | Ensure `close_fds=True` in hermes-display-start |
| Robot too big/small | Edit `s = 2.0` in display.py draw_robot() |
| Port conflict | Change TCP_PORT in display.py + sender.py |
