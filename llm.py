import json
import os
import re
from dotenv import load_dotenv
from groq import Groq
from tool import (
    list_files, read_file, run_command, run_terminal_command,
    search_in_file, split_command, workspace_root, write_file,
)

load_dotenv()

# --- System prompt: tells the AI who it is and what tools it can use ---

SYSTEM_PROMPT = """You are Sana, a helpful AI coding assistant.

If you need to perform an action, reply with ONLY valid JSON like this:
{"tool": "read_file", "path": "file.py"}

When the user asks to create, edit, or run something, you MUST use a tool.
For HTML/webpage requests, write a complete self-contained index.html file.

Available tools:
- read_file(path)                 - Read a file
- write_file(path, content)       - Write to a file
- run_command(command)             - Run a shell command (has safety checks)
- list_files(path)                - List files in a directory
- search_in_file(path, query)     - Search text inside a file
- run_terminal_command(command, cwd?, timeout_seconds?) - Run any command (full access)
- workspace_root()                - Get home directory path
- split_command(command)          - Split command into tokens

If no tool is needed, just reply in plain text.
"""

# --- LLM client setup ---

client = None
current_model = None


def init_client():
    """Set up the Groq client using env vars."""
    global client, current_model
    api_key = os.getenv("GROQ_API_KEY")
    current_model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    if api_key:
        client = Groq(api_key=api_key)


def ask_llm(messages):
    """Send messages to the LLM and return its text response."""
    response = client.chat.completions.create(
        model=current_model,
        messages=messages,
        temperature=0.7,
        max_tokens=1024,
    )
    return response.choices[0].message.content or ""


# --- Tool routing: maps tool name -> function call ---

TOOL_REGISTRY = {
    "read_file":            lambda tc: read_file(tc.get("path")),
    "write_file":           lambda tc: write_file(tc.get("path"), tc.get("content", "")),
    "run_command":          lambda tc: run_command(tc.get("command", "")),
    "list_files":           lambda tc: list_files(tc.get("path", ".")),
    "search_in_file":       lambda tc: search_in_file(tc.get("path"), tc.get("query", "")),
    "run_terminal_command": lambda tc: run_terminal_command(
        tc.get("command", ""), cwd=tc.get("cwd", ""), timeout_seconds=tc.get("timeout_seconds", 30)
    ),
    "workspace_root":       lambda tc: workspace_root(),
    "split_command":        lambda tc: split_command(tc.get("command", "")),
}


def execute_tool(tool_call):
    """Run the tool specified in the tool_call dict."""
    name = tool_call.get("tool")
    handler = TOOL_REGISTRY.get(name)
    if handler:
        return handler(tool_call)
    return f"Unknown tool: {name}"


# --- Parsing: extract tool JSON from LLM output ---

def extract_tool_call(text):
    """Try to find a valid JSON tool call in the LLM's response."""
    if not text:
        return None

    candidate = text.strip()

    # Handle code fences: ```json ... ```
    if candidate.startswith("```"):
        for part in candidate.split("```"):
            cleaned = part.strip()
            if cleaned.startswith("json"):
                cleaned = cleaned[4:].strip()
            if cleaned.startswith("{") and cleaned.endswith("}"):
                candidate = cleaned
                break

    # Handle text mixed with JSON
    if not (candidate.startswith("{") and candidate.endswith("}")):
        for match in re.findall(r"\{[\s\S]*?\}", candidate):
            if '"tool"' in match:
                candidate = match
                break

    # Try to parse
    try:
        data = json.loads(candidate)
        if isinstance(data, dict) and "tool" in data:
            return data
    except json.JSONDecodeError:
        pass
    return None


def looks_like_tool_call(text):
    """Quick check: does the text look like it was trying to be a tool call?"""
    if not text:
        return False
    lower = text.lower()
    return '"tool"' in lower and any(name in lower for name in TOOL_REGISTRY)


# --- Detection: should the AI be forced to use a tool? ---

FORCE_TOOL_KEYWORDS = [
    "create file", "make file", "write file", "save file",
    "update file", "edit file", "in environment", "in workspace",
    "create a static webpage", "create webpage", "html", "tailwind",
]

WEB_KEYWORDS = ["html", "webpage", "website", "landing page", "twind", "tailwind"]


def should_force_tool(user_input):
    """Does the user's message imply they want a file/command action?"""
    text = user_input.lower()
    return any(kw in text for kw in FORCE_TOOL_KEYWORDS)


def is_web_request(user_input):
    """Is the user asking for a webpage?"""
    text = user_input.lower()
    return any(kw in text for kw in WEB_KEYWORDS)


# --- Quality checks for write_file calls ---

def check_write_quality(user_input, tool_call):
    """Validate write_file output. Returns an error string or None if OK."""
    if tool_call.get("tool") != "write_file":
        return None

    path = str(tool_call.get("path", "")).lower()
    content = str(tool_call.get("content", ""))
    prompt = user_input.lower()
    content_lower = content.lower()

    if not content.strip():
        return "File content is empty."

    # Extra checks for HTML files
    if is_web_request(user_input) and path.endswith(".html"):
        if "<!doctype html" not in content_lower:
            return "HTML is incomplete (missing doctype)."
        if "content will be added here" in content_lower:
            return "HTML still has placeholder content."
        if "twind" in prompt and "@twind/core" not in content_lower:
            return "Missing Twind CDN."
        if "vanilla" in prompt and "<script" not in content_lower:
            return "Missing script block for vanilla JS."
        if "animation" in prompt and not any(
            kw in content_lower for kw in ["animate", "transition", "@keyframes"]
        ):
            return "Missing animation styles."
        if "blur" in prompt and "blur" not in content_lower:
            return "Missing blur effects."
        if "responsive" in prompt and not any(
            kw in content_lower for kw in ["sm:", "md:", "lg:", "@media", "viewport"]
        ):
            return "Missing responsive design."
        if "different font" in prompt or "font for each text" in prompt:
            font_count = (
                content_lower.count("font-family") >= 2
                or content_lower.count("font-") >= 3
                or content_lower.count("fonts.googleapis.com") >= 1
            )
            if not font_count:
                return "Missing multiple font styles."

    return None


# --- Main agent loop ---

def run_agent_turn(messages, user_input, max_rounds=5):
    """Handle one user message. May call tools multiple times before responding."""
    messages.append({"role": "user", "content": user_input})

    force_tool = should_force_tool(user_input)
    already_asked_for_tool = False

    for _ in range(max_rounds):
        reply = ask_llm(messages)
        tool_call = extract_tool_call(reply)

        # No tool call found
        if not tool_call:
            # If we expected a tool call, ask the LLM to try again (once)
            if force_tool and (not already_asked_for_tool or looks_like_tool_call(reply)):
                already_asked_for_tool = True
                hint = ""
                if looks_like_tool_call(reply):
                    hint = "Your response looked like a tool call but had invalid JSON. "
                messages.append({"role": "assistant", "content": reply})
                messages.append({
                    "role": "user",
                    "content": (
                        f"{hint}You must use a tool for this request. "
                        "Return ONLY valid JSON (no markdown, no extra text). "
                        "For webpages, write to index.html."
                    ),
                })
                continue

            # Otherwise, just return the plain text reply
            messages.append({"role": "assistant", "content": reply})
            return reply

        # Tool call found - check quality first
        issue = check_write_quality(user_input, tool_call)
        if issue:
            messages.append({"role": "assistant", "content": reply})
            messages.append({
                "role": "user",
                "content": (
                    f"Not acceptable: {issue} "
                    "Regenerate with complete content in one write_file call."
                ),
            })
            continue

        # Run the tool
        tool_output = execute_tool(tool_call)
        messages.append({"role": "assistant", "content": reply})

        # If a file was written successfully, we're done
        if tool_call.get("tool") == "write_file" and isinstance(tool_output, dict) and tool_output.get("ok"):
            done_msg = f"Done. {tool_output.get('message', 'File written.')}"
            messages.append({"role": "assistant", "content": done_msg})
            return done_msg

        # Otherwise, give tool output back to the LLM for a follow-up
        messages.append({
            "role": "user",
            "content": (
                f"Tool result:\n{tool_output}\n\n"
                "If done, answer in plain text. Don't call another tool unless needed."
            ),
        })

    # Ran out of rounds
    fallback = "I hit the tool-call limit. Please try a simpler request."
    messages.append({"role": "assistant", "content": fallback})
    return fallback


if __name__ == "__main__":
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit"]:
            print("Goodbye!")
            break

        reply = run_agent_turn(messages, user_input)
        print(f"Sana: {reply}")
