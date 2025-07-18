# 🚀 TermiGenius

> Transform natural language into terminal commands with AI power

TermiGenius is a globally usable AI-powered command-line tool that translates natural language descriptions into precise terminal commands. Just describe what you want to do, and TermiGenius will generate the appropriate command for you.

## ✨ Features
- 🧠 AI-Powered Translation: Converts human task descriptions into shell commands
- ✅ Safety First: Built-in command validation and safety checks
- 🔐 Secure: Confirmation required before executing any command
- 🌍 Cross-Platform: Works on Linux, macOS, and Windows
- 📚 Smart History: Learns from your usage patterns
- 💬 Chat Mode: Interactive conversation with AI assistant
- 🎨 Beautiful UI: Rich terminal interface with colors and formatting
- 🔧 Configurable: Customizable safety levels and preferences

## 🚀 Quick Start

### Installation
```bash
pip install -e .
```

### Setup
1. Get a Gemini API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Configure TermiGenius:
   ```bash
   termigenius --configure
   ```

### Usage
```bash
termigenius "delete all PDF files from Downloads older than 7 days"
termigenius --explain "compress the logs folder"
termigenius --dry-run "install package"
termigenius --chat
termigenius --history
```

## 🔧 Configuration
TermiGenius can be configured through:
- Configuration file: `~/.termigenius/config.yaml`
- Environment variables: `GEMINI_API_KEY`, `TERMIGENIUS_SAFETY_LEVEL`
- Command line: `termigenius --configure`

## 🛡️ Safety Features
- Command Validation: Blocks dangerous commands
- Safety Levels: Configurable risk tolerance
- Confirmation Required: Always asks before executing
- Pattern Detection: Identifies risky patterns
- Safe Mode: Extra protection for critical operations

## 🤝 Contributing
We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. 