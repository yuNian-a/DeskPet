# Hermes Display

Cartoon cyberpunk status display for secondary USB monitors (596x480 by default, configurable).

## What It Does

Shows a cute robot character on your mini display that changes poses to match your AI agent's current state:

| State | Robot Pose | When |
|-------|-----------|------|
| ANALYZING | Thinking (chin on hand, squinty eyes, "?") | Agent is reasoning |
| EXECUTING | Working (bouncing, swinging arms, gear spinning) | Running tools |
| DISPLAY | Waiting (pulsing circle, "WAITING...") | Clarify / awaiting user |
| IDLE | Resting (lying down, "zZz", half-closed eyes) | Agent is idle |
| SUCCESS | Green "OK" + particle explosion | Task completed |
| FAILURE | Red "FAIL" + shattering fragments | Task failed |
| CRITICAL | Flashing "WARNING" + red alert | System error |

## Quick Start

```bash
# 1. Install
pip install pygame

# 2. Start the display (runs in background)
cd display
python display.py --pos 0,1440

# 3. Send test states
python sender.py 1 "Testing..."
python sender.py 3 "Running tools"
python sender.py 8
```

### One-Click Launch

```batch
# Install everything once:
D:\workspace\hermes display\install.bat

# Then start Hermes + Display together:
D:\workspace\hermes display\hermes_launcher.bat

# Stop display:
D:\workspace\hermes display\stop.bat
```

This automatically:
1. Starts the display daemon if not running
2. Verifies hooks are installed
3. Launches Hermes in WSL

## Integration

### Hermes Agent (WSL)
```bash
cd hooks
python install.py          # Auto-modifies conversation_loop.py
# Restart Hermes to load hooks
```

### Cursor
```bash
# 用户级安装（所有项目生效）
python hooks/install_agents.py

# 或项目级安装（仅当前仓库）
python hooks/install_agents.py --project
```
安装后重启 Cursor。钩子会自动在以下事件更新副屏状态：
- 提交 prompt → ANALYZING
- 执行工具 → EXECUTING / PROCESSING
- 任务完成 → SUCCESS → IDLE

项目模板已包含在 `.cursor/hooks.json`。

### Claude Code
```bash
# 用户级安装
python hooks/install_agents.py

# 或项目级安装
python hooks/install_agents.py --project
```
安装后重启 Claude Code。配置写入 `~/.claude/settings.json`（或项目 `.claude/settings.json`）。

检查安装状态：
```bash
python hooks/install_agents.py --check
```

### 手动集成（任意 Agent）
```python
from display.sender import send
send(1, "Analyzing...")    # Before agent runs
# ... run agent ...
send(4, "Done")            # After agent completes
```

### Any Agent (curl / netcat)
```bash
echo '{"state":1,"msg":"thinking"}' | nc 127.0.0.1 19876
```

### Custom Agent (Python)
```python
from display.sender import send
send(1, "Starting task")
# ... do work ...
send(4, "All done")
```

## Customization

Edit `display/display.py` globals:

| Variable | Default | Description |
|----------|---------|-------------|
| SCREEN_W, SCREEN_H | 596, 480 | Display resolution |
| CORNER_RADIUS | 18 | Rounded corner mask |
| SCALE | 2.0 | Robot character size |
| TCP_PORT | 19876 | Communication port |

## Protocol

TCP JSON messages to `127.0.0.1:19876`:

```json
{"state": 1, "msg": "Analyzing request..."}
```

States: 0=BOOT 1=ANALYZING 2=PROCESSING 3=EXECUTING 4=SUCCESS 5=FAILURE 6=CRITICAL 7=DISPLAY 8=IDLE
