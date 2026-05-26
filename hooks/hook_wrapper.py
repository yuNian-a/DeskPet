#!/usr/bin/env python3
"""
Wrapper to ensure stdin is properly passed to display_hook.py
"""
import subprocess
import sys

# Read all stdin
stdin_data = sys.stdin.read()

# Log to file for debugging
with open("D:/CODE/hooks/hook_debug.log", "a") as f:
    f.write(f"=== Hook called ===\n")
    f.write(f"Args: {sys.argv}\n")
    f.write(f"Stdin: {repr(stdin_data[:500])}\n")

# Pass it to the actual hook
result = subprocess.run(
    [sys.executable, "D:/CODE/hooks/hooks/display_hook.py"],
    input=stdin_data,
    capture_output=True,
    text=True
)

# Log result
with open("D:/CODE/hooks/hook_debug.log", "a") as f:
    f.write(f"Return code: {result.returncode}\n")
    f.write(f"Stderr: {result.stderr}\n")
    f.write(f"---\n")

# Print stderr
if result.stderr:
    print(result.stderr, file=sys.stderr)

sys.exit(result.returncode)
