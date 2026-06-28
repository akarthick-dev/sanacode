import os
import time
from dotenv import load_dotenv, set_key
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text
import rich.box

from llm import SYSTEM_PROMPT, run_agent_turn, init_client

# Colors
BG = "#18181A"
ACCENT = "#ffd1dc"
console = Console(style=f"on {BG}")


def setup_config(change=False):
    """Ask user for API key and model. Saves to .env file."""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(env_path):
        open(env_path, "a").close()

    load_dotenv(env_path)
    api_key = os.getenv("GROQ_API_KEY")
    model = os.getenv("GROQ_MODEL")

    if change or not api_key:
        api_key = Prompt.ask(f"[bold {ACCENT}]Enter your Groq API Key[/bold {ACCENT}]").strip()
        set_key(env_path, "GROQ_API_KEY", api_key)
        os.environ["GROQ_API_KEY"] = api_key

    if change or not model:
        default = "openai/gpt-oss-20b"
        model = Prompt.ask(f"[bold {ACCENT}]Enter LLM Model (default: {default})[/bold {ACCENT}]").strip()
        if not model:
            model = default
        set_key(env_path, "GROQ_MODEL", model)
        os.environ["GROQ_MODEL"] = model

    init_client()


def show_banner():
    """Show the welcome banner."""
    console.print(
        Panel(
            f"[bold {ACCENT}]Sana AI[/bold {ACCENT}]\n"
            "[dim]Commands: /exit, /clear, /history, /config[/dim]",
            border_style=ACCENT,
            box=rich.box.ROUNDED,
        )
    )


def typewriter(label, message, delay=0.006):
    """Print text one character at a time (skip for long messages)."""
    console.print(Text(f"{label}: ", style=f"bold {ACCENT}"), end="")
    if len(message) > 700:
        console.print(message)
        return
    for ch in message:
        console.print(ch, end="", soft_wrap=True)
        time.sleep(delay)
    console.print()


def show_history(history):
    """Display past conversation in a panel."""
    if not history:
        console.print("[dim]No chat history yet.[/dim]")
        return

    lines = []
    for i, item in enumerate(history, 1):
        lines.append(f"{i}. You: {item['user']}")
        lines.append(f"   Sana: {item['assistant']}")

    console.print(
        Panel(
            "\n".join(lines),
            title="Chat History",
            border_style=ACCENT,
            box=rich.box.ROUNDED,
        )
    )


def main():
    console.clear()
    setup_config()
    show_banner()

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    history = []

    while True:
        # Get user input
        try:
            user_input = Prompt.ask(f"[bold {ACCENT}]You[/bold {ACCENT}]").strip()
        except KeyboardInterrupt:
            console.print(f"\n[bold {ACCENT}]Sana:[/bold {ACCENT}] Bye.")
            break

        if not user_input:
            continue

        # Handle commands
        cmd = user_input.lower()

        if cmd in ["/exit", "exit", "quit"]:
            console.print(f"[bold {ACCENT}]Sana:[/bold {ACCENT}] Bye.")
            break

        if cmd in ["/config", "config"]:
            setup_config(change=True)
            console.print(f"[bold {ACCENT}]Sana:[/bold {ACCENT}] Config updated.")
            continue

        if cmd in ["/clear", "clear"]:
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            history.clear()
            console.clear()
            show_banner()
            continue

        if cmd in ["/history", "history"]:
            show_history(history)
            continue

        # Get AI response
        with console.status("[bold]Sana is thinking...[/bold]", spinner="dots"):
            reply = run_agent_turn(messages, user_input)

        history.append({"user": user_input, "assistant": reply})

        try:
            typewriter("Sana", reply)
        except KeyboardInterrupt:
            console.print(f"\n[bold {ACCENT}]Sana:[/bold {ACCENT}] Output interrupted.")


if __name__ == "__main__":
    main()