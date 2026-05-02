import os
import time
from dotenv import load_dotenv, set_key

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text
import rich.box

from llm import SYSTEM_PROMPT, run_agent_turn, init_client


BG_COLOR = "#18181A"
ACCENT = "#ffd1dc"
console = Console(style=f"on {BG_COLOR}")


def setup_config(change=False):
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
        default_model = "llama-3.3-70b-versatile"
        model = Prompt.ask(
            f"[bold {ACCENT}]Enter LLM Model (default: {default_model})[/bold {ACCENT}]"
        ).strip()
        if not model:
            model = default_model
        set_key(env_path, "GROQ_MODEL", model)
        os.environ["GROQ_MODEL"] = model

    init_client()


def print_intro():
    console.print(
        Panel(
            f"[bold {ACCENT}]Sana Code[/bold {ACCENT}]\n"
            "[dim]AI coding assistant with tools[/dim]\n"
            "[dim]Commands: /exit, /clear, /history, /config[/dim]",
            border_style=ACCENT,
            box=rich.box.ROUNDED,
        )
    )


def typewriter_print(label, message, delay=0.006):
    header = Text(f"{label}: ", style=f"bold {ACCENT}")
    console.print(header, end="")
    if len(message) > 700:
        console.print(message)
        return
    for ch in message:
        console.print(ch, end="", soft_wrap=True)
        time.sleep(delay)
    console.print()


def render_history(history):
    if not history:
        console.print("[dim]No chat history yet.[/dim]")
        return

    lines = []
    for i, item in enumerate(history, 1):
        user_line = f"{i}. You: {item['user']}"
        ai_line = f"   Sana: {item['assistant']}"
        lines.extend([user_line, ai_line])
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
    print_intro()

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    history = []

    while True:
        try:
            user_input = Prompt.ask(f"[bold {ACCENT}]You[/bold {ACCENT}]").strip()
        except KeyboardInterrupt:
            console.print(f"\n[bold {ACCENT}]Sana:[/bold {ACCENT}] Bye.")
            break
        if not user_input:
            continue

        command = user_input.lower()
        if command in ["/exit", "exit", "quit"]:
            console.print(f"[bold {ACCENT}]Sana:[/bold {ACCENT}] Bye.")
            break
            
        if command in ["/config", "config"]:
            setup_config(change=True)
            console.print(f"[bold {ACCENT}]Sana:[/bold {ACCENT}] Configuration updated.")
            continue

        if command in ["/clear", "clear"]:
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            history.clear()
            console.clear()
            print_intro()
            continue

        if command in ["/history", "history"]:
            render_history(history)
            continue

        with console.status("[bold]Sana is thinking...[/bold]", spinner="dots"):
            reply = run_agent_turn(messages, user_input)

        history.append({"user": user_input, "assistant": reply})
        try:
            typewriter_print("Sana", reply)
        except KeyboardInterrupt:
            console.print(f"\n[bold {ACCENT}]Sana:[/bold {ACCENT}] Output interrupted.")


if __name__ == "__main__":
    main()