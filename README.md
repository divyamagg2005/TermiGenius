# 🚀 TermiGenius

**Transform natural language into safe, native terminal commands with AI.**

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [How It Works](#how-it-works)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
  - [Basic Command](#basic-command)
  - [Options](#options)
  - [Subcommands](#subcommands)
- [Safety & Validation](#safety--validation)
- [Command History](#command-history)
- [AI & Prompt Engineering](#ai--prompt-engineering)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [License](#license)
- [Author & Credits](#author--credits)

---

## Overview

**TermiGenius** is an AI-powered command-line tool that translates natural language descriptions into precise, safe, and native terminal commands for your operating system. It leverages Google Gemini for AI, robust prompt engineering, and strict validation to ensure commands are both effective and secure.

---

## Features

- 🧠 **AI-Powered Translation:** Converts human task descriptions into native shell commands.
- 🛡️ **Safety First:** Built-in command validation, risk detection, and user confirmation.
- 🔐 **Secure:** Never executes a command without your explicit approval (unless auto-confirm is enabled).
- 🌍 **Cross-Platform:** Works on Linux, macOS, and Windows, always generating native commands.
- 📚 **Smart History:** Tracks your command usage for review and learning.
- 💬 **Chat Mode:** Interactive conversation with the AI assistant.
- 🎨 **Beautiful UI:** Rich terminal interface with colors, panels, and tables.
- 🔧 **Configurable:** Customizable safety levels, preferences, and API keys.

---

## How It Works

1. **You describe a task in plain English.**
2. **TermiGenius** sends your prompt, along with detailed system context, to the Gemini AI.
3. The AI generates a **native, safe, and absolute-path terminal command** for your OS and shell.
4. The command is validated for safety and shown to you for confirmation.
5. Upon approval, the command is executed and the result is displayed.
6. All actions are logged in your command history (if enabled).

---

## Installation

```bash
git clone https://github.com/divyamagg2005/TermiGenius.git
cd TermiGenius
pip install -e .
```

---

## Configuration

1. **Get a Gemini API key** from Google AI Studio.
2. **Configure TermiGenius:**
   ```bash
   termigenius configure
   ```
   - Enter your API key.
   - Set safety level (`high`, `medium`, `low`).
   - Choose auto-confirm and history preferences.

Configuration is stored in `~/.termigenius/config.yaml`.  
You can also use environment variables: `GEMINI_API_KEY`, `TERMIGENIUS_SAFETY_LEVEL`.

---

## Usage

### Basic Command

```bash
termigenius run "delete all PDF files from Downloads older than 7 days"
```

### Options

- `--explain, -e` : Show a detailed explanation of the generated command.
- `--dry-run, -d` : Show the command but do not execute it.
- `--safe-mode, -s` : Enable extra safety checks.
- `--advanced-context` : Send advanced system context to Gemini (see docs for privacy).

### Subcommands

- `termigenius configure` : Configure API key and preferences.
- `termigenius history` : Show your recent command history.
- `termigenius chat` : Enter interactive chat mode with the AI.

---

## Safety & Validation

- **CommandValidator** checks for dangerous patterns, risky operations, and enforces your chosen safety level.
- **User confirmation** is always required before execution (unless auto-confirm is enabled).
- **Dry-run mode** lets you preview commands without running them.
- **Safe mode** blocks or warns about potentially destructive commands.

---

## Command History

- All executed commands (if enabled) are logged in `~/.termigenius/history.json`.
- View your history with:
  ```bash
  termigenius history
  ```
- History includes prompt, command, timestamp, success status, and execution time.

---

## AI & Prompt Engineering

- Uses **Google Gemini** via the official `google-generativeai` SDK.
- **Ultra-robust prompt templates** ensure only native, OS-appropriate commands are generated.
- System context (OS, shell, user, available commands, etc.) is sent to the AI for maximum accuracy.
- Prompts strictly forbid cross-platform command errors (e.g., no `ls` on Windows).

---

## Project Structure

```
src/termigenius/
├── cli.py           # Main Typer CLI entry point
├── core/
│   ├── executor.py      # Command execution logic
│   ├── validator.py     # Command validation and safety
│   ├── history.py       # Command history management
├── ai/
│   ├── gemini.py        # Gemini AI provider and context builder
│   ├── prompts.py       # Prompt templates for command generation, explanation, safety
├── utils/
│   ├── config.py        # Configuration management (YAML, env, .env)
│   ├── ui.py            # Rich terminal UI components
│   ├── helpers.py       # System info, shell detection, etc.
├── data/
│   ├── safety_rules.json    # (Optional) Extra safety rules
│   ├── commands.json        # (Optional) List of known commands
```

---

## Contributing

Contributions are welcome!  
- Fork the repo and submit a pull request.
- Please follow the code style and add tests for new features.
- See the [GitHub repository](https://github.com/divyamagg2005/TermiGenius) for issues and discussions.

---

## License

This project is licensed under the MIT License.  
See the [LICENSE](LICENSE) file for details.

---

## Author & Credits

- **Author:** Divyam Aggarwal  
- **Email:** divyamagg2005@gmail.com  
- **GitHub:** [divyamagg2005/TermiGenius](https://github.com/divyamagg2005/TermiGenius)

---

**TermiGenius** — Transforming natural language into safe, native terminal power with AI. 