# Sana AI

A terminal AI agent powered by MCP tools. It can interact with your system — read/write files, run commands, list directories, and more — all through natural chat.

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

On first run it will ask for your [Groq API key](https://console.groq.com/) and model name.

## Chat Commands

| Command    | What it does              |
|------------|---------------------------|
| `/exit`    | Quit                      |
| `/clear`   | Clear chat and screen     |
| `/history` | Show past messages        |
| `/config`  | Change API key or model   |

## MCP Tools

All tools are defined in `tool.py` as an MCP server using [FastMCP](https://github.com/modelcontextprotocol/python-sdk). They can be called by the agent during chat, or you can run the server standalone:

```bash
python tool.py
```

| Tool                   | What it does                          |
|------------------------|---------------------------------------|
| `read_file`            | Read a file                           |
| `write_file`           | Write content to a file               |
| `run_command`          | Run a shell command (with safety)     |
| `list_files`           | List files in a folder                |
| `search_in_file`       | Search text inside a file             |
| `run_terminal_command` | Run any command (custom dir/timeout)  |
| `workspace_root`       | Get home directory path               |
| `split_command`        | Split a command into tokens           |

## Files

| File               | Purpose                              |
|--------------------|--------------------------------------|
| `main.py`          | Entry point, terminal UI, chat loop  |
| `llm.py`           | LLM client, system prompt, agent     |
| `tool.py`          | MCP tool server (FastMCP)            |
| `stt.py`           | Speech-to-text (optional)            |
| `voice.py`         | Text-to-speech (optional)            |
| `requirements.txt` | Python packages                      |

## Config (.env)

| Variable                  | Required | Default                   |
|---------------------------|----------|---------------------------|
| `GROQ_API_KEY`            | Yes      | -                         |
| `GROQ_MODEL`              | No       | `llama-3.3-70b-versatile` |
| `SANA_INTERACTIVE_CONFIRM`| No       | `0`                       |
| `HF_TOKEN`                | No       | - (for STT)               |
| `VOICE_ID`                | No       | - (for TTS)               |
| `ELEVEN_LABS_API_KEY`     | No       | - (for TTS)               |
