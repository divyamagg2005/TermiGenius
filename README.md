	Disclaimer:
TermiGenius is an open-source productivity tool designed to assist developers and system administrators by converting natural language into terminal commands.

	This software is not intended to be used for unethical or illegal purposes, including but not limited to:
		•	Bypassing institutional or organizational restrictions.
	•	Gaining unfair advantage during tests, exams, or assessments.
	•	Any activity that violates academic or workplace integrity policies.

	The author of TermiGenius does not condone or encourage any misuse of this tool. Users are solely responsible for how they choose to use TermiGenius. The author will not be held liable for any consequences, damages, or violations arising from unethical or illegal use of this software.

	By using TermiGenius, you agree to comply with all applicable laws, regulations, and institutional policies.

# 🚀 TermiGenius

> **AI-powered natural language → PowerShell command translator for Windows**

TermiGenius transforms your everyday English requests into **safe, native, and validated PowerShell commands**. It confirms, explains, executes, and logs every command—so you stay in control. Built for Windows, it leverages Google Gemini AI and rigorous safety checks to ensure every command is both effective and secure.

---

## ✨ Features

- **Google Gemini AI**: Converts plain English to native PowerShell (no cross-platform mistakes)
- **Safety-first**: Static analysis, risk scoring, and interactive confirmation
- **Rich TUI**: Beautiful output, panels, and spinners (powered by [Rich](https://github.com/Textualize/rich))
- **Explain-before-execute**: `--explain` gives a detailed breakdown of every command
- **Interactive chat**: Run multiple commands in a session
- **Smart history**: Local JSON log with prompt, command, timestamps, and results
- **Configurable**: YAML config, environment variable overrides, and interactive setup
- **Extensible**: Modular design for AI, validation, and UI

---

## 🏁 Quickstart

**Requirements:**
- Windows 10/11
- Python 3.9+

```powershell
git clone https://github.com/divyamagg2005/TermiGenius.git
cd TermiGenius
pip install -e .
termigenius configure  # Enter your Gemini API key and preferences
```

---

## 🚀 Usage: CLI Commands

### 1. `run` — Generate and Execute a Command

Generate a PowerShell command from natural language, optionally explain it, and execute it after your confirmation.

```powershell
termigenius run "show my IP address" 
```



**Example Output:**
```
💡 Generated Command for: 'show my IP address'
Get-NetIPAddress | Where-Object { $_.AddressFamily -eq 'IPv4' -and !$_.IPAddresses -match '169.254' }

then asks for confirmation whether user wants to run the command or not . 


---

### 2. `chat` — Interactive Chat Mode

Conversational mode: keep sending natural language requests, get commands, explanations, and run them in sequence.

```powershell
termigenius chat
```

**How it works:**
- Type your request (e.g., `find all large files on C:`)
- The AI generates and validates a command
- You can ask for explanations, approve, or skip
- Type `quit` or `exit` to leave chat mode

**Example Session:**
```
🤖 What would you like to do?
> list all running processes
💡 Generated Command: Get-Process
❓ Do you want to execute this command? [Y/n]
✅ Command executed. Output: ...
```

---

### 3. `history` — View Command History

Show your recent command history, including prompts, commands, timestamps, and status.

```powershell
termigenius history
```

**Example Output:**
```
📝 Command History
Date                Prompt                  Command                Status
2024-06-01 10:00    show my IP address      Get-NetIPAddress ...   ✅
2024-06-01 10:05    delete temp files       Remove-Item ...        ✅
...
```

---

### 4. `configure` — Interactive Configuration

Set up or update your Gemini API key, safety level, auto-confirm, and history preferences.

```powershell
termigenius configure
```

**Prompts:**
- Gemini API key (input is hidden)
- Safety level: `high` (default), `medium`, `low`
- Auto-confirm: Run safe commands automatically? (y/n)
- History: Enable/disable local logging

**Config file:** `%USERPROFILE%\.termigenius\config.yaml`

**Environment variable overrides:**
- `GEMINI_API_KEY`
- `TERMIGENIUS_SAFETY_LEVEL`

---

### 5. `explain` — Explain Any PowerShell Command

Get a detailed, multi-section explanation for any PowerShell command (even ones you write yourself).

```powershell
termigenius run "prompt" --explain

**Example Output:**
```
📚 Command Explanation
<<<<<<<<command explanation>>>>>>>>
...
```

---

## 🛠️ How It Works: Full Workflow

1. **User Input:**
   - You provide a natural language prompt (e.g., "find all PDF files in Downloads older than 7 days").

2. **System Context Gathering:**
   - TermiGenius collects detailed Windows and PowerShell context (user, OS, available modules, drives, privileges, etc.).

3. **AI Command Generation:**
   - The prompt and system context are sent to Google Gemini with strict instructions to generate a native, safe PowerShell command (no aliases, no Unix/CMD commands, only full cmdlets, all paths absolute).

4. **Validation:**
   - The generated command is checked by the CommandValidator:
     - Blocks dangerous patterns (e.g., `Remove-Item -Recurse C:\`)
     - Warns about risky operations
     - Ensures only allowed cmdlets and parameters are used
     - Checks for absolute paths, privilege requirements, and more

5. **Explanation (Optional):**
   - If `--explain` is used, the command is sent back to Gemini for a detailed, multi-section explanation (purpose, parameters, safety, alternatives, troubleshooting, etc.).

6. **User Confirmation:**
   - You review the command and explanation, then approve or reject execution (unless auto-confirm is enabled).

7. **Execution:**
   - The command is run via `powershell.exe` with full cmdlet support. Output and errors are captured.

8. **History Logging:**
   - Every action (prompt, command, result, timestamp, duration) is logged to `%USERPROFILE%\.termigenius\history.json` (if enabled).

9. **Rich TUI:**
   - All interactions use [Rich](https://github.com/Textualize/rich) for beautiful panels, tables, and spinners.

---

## 🏗️ Architecture Diagram

```
User prompt
   │
   ▼
[CLI (Typer)]
   │
   ▼
[GeminiProvider (AI)]
   │
   ▼
[CommandValidator]
   │
   ▼
[Executor] ──▶ [HistoryManager]
   │
   ▼
[Rich TUI]
```

- **CLI**: Typer-based, commands: `run`, `chat`, `history`, `configure`, `explain`
- **GeminiProvider**: Calls Gemini, applies strict prompt templates, extracts commands, explains
- **CommandValidator**: Pure-Python static checker for safety
- **Executor**: Runs commands via `powershell.exe` (full cmdlet support)
- **HistoryManager**: JSON log under `%USERPROFILE%\.termigenius\history.json`

---

## 📂 Project Structure

```
src/termigenius/
├── cli.py           # Main CLI entry point
├── ai/              # GeminiProvider, prompt templates
├── core/            # Executor, Validator, HistoryManager
├── utils/           # Config, UI, helpers
├── data/            # Safety rules, (optional) command lists
```

---

## ⚙️ Advanced Configuration

- **Config file:** `%USERPROFILE%\.termigenius\config.yaml`
- **History file:** `%USERPROFILE%\.termigenius\history.json`
- **Environment variables:**
  - `GEMINI_API_KEY`: Your Gemini API key
  - `TERMIGENIUS_SAFETY_LEVEL`: `high`, `medium`, or `low`
- **.env support:** Place a `.env` file in your project directory for local overrides
- **Max history:** Default 100 entries (configurable)
- **Preferred shell:** (for future extensibility)

---

## 🧩 Troubleshooting & Tips

- **Gemini API key not found:** Run `termigenius configure` or set `GEMINI_API_KEY` in your environment.
- **Command validation failed:** Review the error and suggestion. You can lower the safety level if needed.
- **No output or errors:** Use `--explain` to understand what the command does before running.
- **History not saving:** Ensure history is enabled in your config.
- **Permission errors:** Some commands require admin rights. Run your terminal as Administrator if needed.
- **Windows only:** TermiGenius is designed for Windows and PowerShell. It will not run on Linux or macOS.

---

## 🤝 Contributing

PRs are welcome! Please:
- Open an issue for major changes
- Ensure tests pass (`pytest`) and code is formatted (`black`)
- Follow docstring and typing style

---

## 📜 License

[MIT](LICENSE)

---

## 👤 Author

**Divyam Aggarwal** – <divyamagg2005@gmail.com>

---

> *TermiGenius – Turn thoughts into terminal power.* 