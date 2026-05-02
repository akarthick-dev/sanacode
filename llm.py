import json
import os
import re
from dotenv import load_dotenv
from groq import Groq
from tool import list_files, read_file, run_command, search_in_file, write_file


load_dotenv()

SYSTEM_PROMPT = """You are Sana, a helpful AI coding assistant.
You help users with writing, editing, and debugging code.

If you need to use a tool, reply with ONLY valid JSON in this format:
{"tool": "read_file", "path": "file.py"}

When a user asks to create, edit, update, save, or run something in their environment,
you MUST use tools instead of only giving code text.
For webpage requests, create files (for example index.html) with write_file.
When creating webpages, always satisfy the user's requested stack and style constraints.
If user asks for beautiful design, animations, blur effects, responsive layout, or human-made look,
generate a complete high-quality page (not placeholder text, not minimal boilerplate).
Never reference local files like styles.css or app.js unless you also create those files in the same turn.
For HTML requests, prefer a fully self-contained index.html unless user asks for multi-file split.

Available tools:
- read_file(path)
- write_file(path, content)
- run_command(command)
- list_files(path)
- search_in_file(path, query)

If no tool is needed, reply normally in plain text.
"""


client = None
current_model = None

def init_client():
    global client, current_model
    api_key = os.getenv("GROQ_API_KEY")
    current_model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    if api_key:
        client = Groq(api_key=api_key)


def execute_tool(tool_call):
    """Route tool calls to the right function."""
    tool = tool_call.get("tool")

    if tool == "read_file":
        return read_file(tool_call.get("path"))
    if tool == "write_file":
        return write_file(tool_call.get("path"), tool_call.get("content", ""))
    if tool == "run_command":
        return run_command(tool_call.get("command", ""))
    if tool == "list_files":
        return list_files(tool_call.get("path", "."))
    if tool == "search_in_file":
        return search_in_file(tool_call.get("path"), tool_call.get("query", ""))

    return f"Unknown tool: {tool}"


def ask_llm(messages):
    response = client.chat.completions.create(
        model=current_model,
        messages=messages,
        temperature=0.7,
        max_tokens=1024,
    )
    return response.choices[0].message.content or ""


def extract_tool_call(text):
    """Extract JSON tool call from plain or fenced assistant output."""
    if not text:
        return None

    candidate = text.strip()
    if candidate.startswith("```"):
        parts = candidate.split("```")
        for part in parts:
            cleaned = part.strip()
            if cleaned.startswith("json"):
                cleaned = cleaned[4:].strip()
            if cleaned.startswith("{") and cleaned.endswith("}"):
                candidate = cleaned
                break

    # Handle mixed output where JSON appears inside additional text.
    if not (candidate.startswith("{") and candidate.endswith("}")):
        matches = re.findall(r"\{[\s\S]*?\}", candidate)
        for snippet in matches:
            if '"tool"' in snippet:
                candidate = snippet
                break

    try:
        payload = json.loads(candidate)
        if isinstance(payload, dict) and "tool" in payload:
            return payload
    except json.JSONDecodeError:
        return None
    return None


def is_probable_tool_call(text):
    if not text:
        return False
    lowered = text.lower()
    return '"tool"' in lowered and ("write_file" in lowered or "read_file" in lowered or "run_command" in lowered or "list_files" in lowered or "search_in_file" in lowered)


def should_force_tool_call(user_input):
    text = user_input.lower()
    trigger_words = [
        "create file",
        "make file",
        "write file",
        "save file",
        "update file",
        "edit file",
        "in environment",
        "in workspace",
        "create a static webpage",
        "create webpage",
        "html",
        "tailwind",
    ]
    return any(word in text for word in trigger_words)


def is_web_request(user_input):
    text = user_input.lower()
    web_words = ["html", "webpage", "website", "landing page", "twind", "tailwind"]
    return any(word in text for word in web_words)


def validate_write_quality(user_input, tool_call):
    """Return None when acceptable, otherwise a short reason string."""
    if tool_call.get("tool") != "write_file":
        return None

    path = str(tool_call.get("path", "")).lower()
    content = str(tool_call.get("content", ""))
    prompt = user_input.lower()
    content_lower = content.lower()

    if not content.strip():
        return "File content is empty."

    if is_web_request(user_input) and path.endswith(".html"):
        if "<!doctype html" not in content_lower:
            return "HTML is incomplete (missing doctype)."
        if "content will be added here" in content_lower:
            return "HTML still contains placeholder content."

        if "twind" in prompt and "@twind/core" not in content_lower:
            return "User asked for Twind CDN but the page does not include it."

        if "vanilla" in prompt and "<script" not in content_lower:
            return "User asked for vanilla JS but no script block was found."

        if "animation" in prompt and not any(
            key in content_lower for key in ["animate", "transition", "@keyframes"]
        ):
            return "User asked for animation but no animation styles/classes were found."

        if "blur" in prompt and "blur" not in content_lower:
            return "User asked for blur effects but no blur styles/classes were found."

        if "responsive" in prompt and not any(
            key in content_lower for key in ["sm:", "md:", "lg:", "@media", "viewport"]
        ):
            return "User asked for responsive design but responsive hints were not found."

        if "different font" in prompt or "font for each text" in prompt:
            has_multiple_fonts = (
                content_lower.count("font-family") >= 2
                or content_lower.count("font-") >= 3
                or content_lower.count("fonts.googleapis.com") >= 1
            )
            if not has_multiple_fonts:
                return "User asked for varied typography but multiple font styles were not found."

    return None


def run_agent_turn(messages, user_input, max_tool_rounds=5):
    """Run one user turn with optional tool execution rounds."""
    messages.append({"role": "user", "content": user_input})

    force_tool = should_force_tool_call(user_input)
    requested_tool_once = False

    for _ in range(max_tool_rounds):
        assistant_reply = ask_llm(messages)
        tool_call = extract_tool_call(assistant_reply)

        if not tool_call:
            if force_tool and (not requested_tool_once or is_probable_tool_call(assistant_reply)):
                requested_tool_once = True
                reason = ""
                if is_probable_tool_call(assistant_reply):
                    reason = (
                        "Your previous response looked like a tool call but was invalid JSON. "
                        "Escape quotes/newlines correctly in JSON strings. "
                    )
                messages.append({"role": "assistant", "content": assistant_reply})
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            f"{reason}"
                            "You must use tools for this request. "
                            "Return ONLY valid minified JSON for the next tool call (no markdown, no extra text). "
                            "If creating a webpage, write it to index.html."
                        ),
                    }
                )
                continue
            messages.append({"role": "assistant", "content": assistant_reply})
            return assistant_reply

        quality_issue = validate_write_quality(user_input, tool_call)
        if quality_issue:
            messages.append({"role": "assistant", "content": assistant_reply})
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "Your tool call is not acceptable yet: "
                        f"{quality_issue} "
                        "Regenerate and return only JSON tool call. "
                        "If writing HTML, provide complete high-quality content in one write_file call."
                    ),
                }
            )
            continue

        tool_output = execute_tool(tool_call)
        messages.append({"role": "assistant", "content": assistant_reply})

        # Avoid looping on repeated writes: if a file was written successfully,
        # finish this turn with a direct confirmation.
        if tool_call.get("tool") == "write_file" and str(tool_output).startswith(
            "Successfully written to"
        ):
            final_reply = f"Done. {tool_output}"
            messages.append({"role": "assistant", "content": final_reply})
            return final_reply

        messages.append(
            {
                "role": "user",
                "content": (
                    f"Tool result:\n{tool_output}\n\n"
                    "If the task is completed, answer the user now in plain text. "
                    "Do not call another tool unless strictly necessary."
                ),
            }
        )

    fallback = "I reached the tool-call limit for this turn. Please try a narrower request."
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
