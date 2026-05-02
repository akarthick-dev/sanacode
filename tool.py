import os
import subprocess
from rich.console import Console


console = Console()
INTERACTIVE_CONFIRM = os.getenv("SANA_INTERACTIVE_CONFIRM", "0") == "1"


def read_file(path):
    """Read a file and return its contents"""
    try:
        with open(path, "r") as f:
            content = f.read()
        console.print(f"[green]✅ Read file: {path}[/green]")
        return content
    except Exception as e:
        return f"Error reading file: {e}"

def write_file(path, content):
    """Write content to a file"""
    try:
        if INTERACTIVE_CONFIRM:
            console.print(f"[yellow]⚠️  Write to {path}? (y/n)[/yellow]", end=" ")
            confirm = input().strip().lower()
            if confirm != "y":
                return "Write cancelled by user"
        with open(path, "w") as f:
            f.write(content)
        console.print(f"[green]✅ Written to: {path}[/green]")
        return f"Successfully written to {path}"
    except Exception as e:
        return f"Error writing file: {e}"

def run_command(command):
    """Run a shell command safely"""
    # Safety check - dangerous commands
    dangerous = ["rm -rf", "format", "del /f", "shutdown", "mkfs"]
    if any(d in command.lower() for d in dangerous):
        console.print(f"[red]❌ Dangerous command blocked: {command}[/red]")
        return "Command blocked for safety"

    if INTERACTIVE_CONFIRM:
        console.print(f"[yellow]⚠️  Run command: `{command}`? (y/n)[/yellow]", end=" ")
        confirm = input().strip().lower()
        if confirm != "y":
            return "Command cancelled by user"

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        output = result.stdout + result.stderr
        console.print(f"[green]✅ Command output:[/green]")
        console.print(output)
        return output
    except subprocess.TimeoutExpired:
        return "Command timed out after 30 seconds"
    except Exception as e:
        return f"Error running command: {e}"

def list_files(path="."):
    """List files in a directory"""
    try:
        files = os.listdir(path)
        return "\n".join(files)
    except Exception as e:
        return f"Error listing files: {e}"

def search_in_file(path, query):
    """Search for a string in a file"""
    try:
        with open(path, "r") as f:
            lines = f.readlines()
        results = []
        for i, line in enumerate(lines, 1):
            if query.lower() in line.lower():
                results.append(f"Line {i}: {line.strip()}")
        return "\n".join(results) if results else "Not found"
    except Exception as e:
        return f"Error searching file: {e}"