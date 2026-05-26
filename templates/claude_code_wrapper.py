"""
Claude Code integration template for Hermes Display.

Copy-paste this into your CLAUDE.md or system prompt, OR
run this script as a wrapper around claude:

    python templates/claude_code_wrapper.py -- "your prompt here"

The wrapper injects display state updates before/after each Claude Code run.
"""

import subprocess
import sys
import os

# Add project root to path so we can import sender
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'display'))
from sender import send

TCP_PORT = 19876


def run_with_display(prompt: str):
    """Run a prompt through Claude Code with display integration."""
    # → ANALYZING
    send(1, prompt[:60])

    try:
        result = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True, text=True, timeout=300
        )

        if result.returncode == 0:
            send(4, "Claude Code completed")
        else:
            send(5, f"Exit code: {result.returncode}")

        return result.stdout
    except subprocess.TimeoutExpired:
        send(5, "Timeout")
        return "ERROR: Timeout"
    except Exception as e:
        send(5, str(e)[:60])
        raise
    finally:
        send(8, "")


if __name__ == "__main__":
    prompt = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Hello"
    print(run_with_display(prompt))
