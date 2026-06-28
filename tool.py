import os
import shlex
import subprocess
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

# Create the MCP server
mcp = FastMCP("sana-tools")

# Settings
INTERACTIVE_CONFIRM = os.getenv("SANA_INTERACTIVE_CONFIRM", "0") == "1"
DEFAULT_TIMEOUT = 30
MAX_TIMEOUT = 600


@mcp.tool(description="Read and return a file's text content.")
def read_file(path: str) -> dict[str, Any]:
    try:
        with open(path, "r") as f:
            content = f.read()
        return {"ok": True, "path": path, "content": content}
    except Exception as e:
        return {"ok": False, "error": f"Error reading file: {e}"}


@mcp.tool(description="Write text content to a file.")
def write_file(path: str, content: str = "") -> dict[str, Any]:
    try:
        if INTERACTIVE_CONFIRM:
            print(f"[WARN] Write to {path}? (y/n) ", end="")
            if input().strip().lower() != "y":
                return {"ok": False, "error": "Write cancelled by user"}

        with open(path, "w") as f:
            f.write(content)
        return {"ok": True, "message": f"Successfully written to {path}"}
    except Exception as e:
        return {"ok": False, "error": f"Error writing file: {e}"}


@mcp.tool(description="Run a shell command with basic safety checks.")
def run_command(command: str) -> dict[str, Any]:
    blocked = ["rm -rf", "format", "del /f", "shutdown", "mkfs"]
    if any(b in command.lower() for b in blocked):
        return {"ok": False, "error": "Command blocked for safety"}

    if INTERACTIVE_CONFIRM:
        print(f"[WARN] Run: {command}? (y/n) ", end="")
        if input().strip().lower() != "y":
            return {"ok": False, "error": "Command cancelled by user"}

    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=30
        )
        return {
            "ok": result.returncode == 0,
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "Command timed out after 30 seconds"}
    except Exception as e:
        return {"ok": False, "error": f"Error running command: {e}"}


@mcp.tool(description="Run any terminal command with optional working directory and timeout.")
def run_terminal_command(
    command: str,
    cwd: str = "",
    timeout_seconds: int = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    command = command.strip()
    if not command:
        return {"ok": False, "error": "command is required"}

    timeout_seconds = max(1, min(int(timeout_seconds), MAX_TIMEOUT))
    workdir = _resolve_cwd(cwd)

    try:
        result = subprocess.run(
            command, shell=True, cwd=workdir,
            capture_output=True, text=True, timeout=timeout_seconds,
        )
        return {
            "ok": result.returncode == 0,
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "cwd": str(workdir),
            "command": command,
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"Timed out after {timeout_seconds}s", "command": command}
    except Exception as e:
        return {"ok": False, "error": str(e), "command": command}


@mcp.tool(description="List all files and folders at the given path.")
def list_files(path: str = ".") -> dict[str, Any]:
    target = Path(path).expanduser().resolve()

    if not target.exists():
        return {"ok": False, "error": f"Path not found: {target}"}
    if not target.is_dir():
        return {"ok": False, "error": f"Not a directory: {target}"}

    entries = []
    try:
        for child in sorted(target.iterdir(), key=lambda p: p.name.lower()):
            entries.append({
                "name": child.name,
                "type": "dir" if child.is_dir() else "file",
                "size": child.stat().st_size if child.is_file() else None,
            })
    except PermissionError:
        return {"ok": False, "error": f"Permission denied: {target}"}

    return {"ok": True, "path": str(target), "entries": entries}


@mcp.tool(description="Search for a string inside a file. Returns matching lines.")
def search_in_file(path: str, query: str = "") -> dict[str, Any]:
    try:
        with open(path, "r") as f:
            lines = f.readlines()

        matches = []
        for i, line in enumerate(lines, 1):
            if query.lower() in line.lower():
                matches.append({"line": i, "content": line.rstrip()})

        return {"ok": True, "path": path, "query": query, "matches": matches}
    except Exception as e:
        return {"ok": False, "error": f"Error searching: {e}"}


@mcp.tool(description="Get the user's home directory path.")
def workspace_root() -> dict[str, str]:
    return {"workspace_root": str(Path.home())}


@mcp.tool(description="Split a shell command string into individual tokens.")
def split_command(command: str) -> dict[str, Any]:
    return {"tokens": shlex.split(command)}


# Helper (not an MCP tool)
def _resolve_cwd(cwd):
    """Turn a cwd string into a valid directory Path. Falls back to home."""
    if not cwd or not str(cwd).strip():
        return Path.home()
    target = Path(cwd).expanduser().resolve()
    if target.exists() and target.is_dir():
        return target
    return Path.home()


# Run as MCP server when executed directly
if __name__ == "__main__":
    mcp.run()
