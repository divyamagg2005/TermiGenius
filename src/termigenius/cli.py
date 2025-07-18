"""
Main CLI interface for TermiGenius
"""

import sys
import typer
from rich.console import Console
from .utils.config import Config
from .utils.ui import TermiGeniusUI
from .ai.gemini import GeminiProvider
from .core.executor import CommandExecutor
from .core.validator import CommandValidator
from .core.history import HistoryManager

app = typer.Typer(
    name="termigenius",
    help="AI-powered natural language to terminal command translator",
    add_completion=False,
)

console = Console()
ui = TermiGeniusUI()

def process_prompt(prompt: str, ai_provider, validator, executor, history_manager, config, explain=False, dry_run=False, safe_mode=False, advanced_context=False):
    with ui.status("🤖 Generating command..."):
        try:
            command = ai_provider.generate_command(prompt, advanced_context=advanced_context)
            validation_result = validator.validate(command, safe_mode)
            if not validation_result.is_safe:
                ui.error(f"🚨 Command validation failed: {validation_result.reason}")
                if validation_result.suggestion:
                    ui.info(f"💡 Suggestion: {validation_result.suggestion}")
                return
            ui.show_command(command, prompt)
            if explain:
                explanation = ai_provider.explain_command(command)
                ui.show_explanation(explanation)
            if dry_run:
                ui.info("🧪 Dry run mode - command not executed")
                return
            if config.auto_confirm or ui.confirm("Do you want to run this command?"):
                result = executor.execute(command)
                history_manager.add_entry(prompt, command, result.success, result.execution_time, len(result.output))
                if result.success:
                    ui.success("✅ Command executed successfully")
                    if result.output:
                        console.print(result.output)
                else:
                    ui.error(f"❌ Command failed: {result.error}")
            else:
                ui.info("👋 Command cancelled")
        except Exception as e:
            ui.error(f"Failed to process prompt: {str(e)}")

def configure_termigenius():
    config = Config.load()
    ui.info("🔧 TermiGenius Configuration")
    current_key = config.gemini_api_key
    update_key = True
    if current_key:
        ui.info(f"Current API key: {current_key[:8]}...")
        update_key = ui.confirm("Update API key?")
    if update_key or not current_key:
        api_key = typer.prompt("Enter your Gemini API key", hide_input=True)
        config.gemini_api_key = api_key
    config.safety_level = typer.prompt("Safety level (high/medium/low)", default=config.safety_level)
    config.auto_confirm = typer.confirm("Enable auto-confirm for safe commands?", default=config.auto_confirm)
    config.history_enabled = typer.confirm("Enable command history?", default=config.history_enabled)
    config.save()
    ui.success("✅ Configuration saved!")

def chat_mode(config: Config):
    ui.info("💬 Chat mode activated. Type 'quit' to exit.")
    ai_provider = get_ai_provider(config)
    validator = CommandValidator(config)
    executor = CommandExecutor(config)
    history_manager = HistoryManager(config)
    while True:
        try:
            prompt = typer.prompt("\n🤖 What would you like to do?")
            if prompt.lower() in ['quit', 'exit', 'bye']:
                ui.info("👋 Goodbye!")
                break
            process_prompt(prompt, ai_provider, validator, executor, history_manager, config)
        except KeyboardInterrupt:
            ui.info("\n👋 Goodbye!")
            break
        except EOFError:
            ui.info("\n👋 Goodbye!")
            break

def get_ai_provider(config: Config):
    if config.ai_provider == "gemini":
        return GeminiProvider(config.gemini_api_key)
    else:
        raise ValueError(f"Unsupported AI provider: {config.ai_provider}")

@ app.command()
def run(
    prompt: str = typer.Argument(..., help="Natural language description of the command"),
    explain: bool = typer.Option(False, "--explain", "-e", help="Explain the command before running"),
    dry_run: bool = typer.Option(False, "--dry-run", "-d", help="Show command but don't execute"),
    safe_mode: bool = typer.Option(False, "--safe-mode", "-s", help="Extra safety checks"),
    advanced_context: bool = typer.Option(False, "--advanced-context", help="Send advanced system context to Gemini (privacy: see docs)")
):
    """Generate and (optionally) execute a shell command from a natural language prompt."""
    try:
        config = Config.load()
        if not config.gemini_api_key:
            ui.error("Gemini API key not found. Please run 'termigenius configure' to set it up.")
            sys.exit(1)
        ai_provider = get_ai_provider(config)
        validator = CommandValidator(config)
        executor = CommandExecutor(config)
        history_manager = HistoryManager(config)
        process_prompt(prompt, ai_provider, validator, executor, history_manager, config, explain, dry_run, safe_mode, advanced_context)
    except KeyboardInterrupt:
        ui.info("\n👋 Goodbye!")
        sys.exit(0)
    except Exception as e:
        ui.error(f"An error occurred: {str(e)}")
        sys.exit(1)

@app.command()
def configure():
    """Configure TermiGenius settings and API key."""
    configure_termigenius()

@app.command()
def history():
    """Show command history."""
    config = Config.load()
    history_manager = HistoryManager(config)
    entries = history_manager.get_recent_entries(20)
    if not entries:
        ui.info("📝 No command history found")
        return
    ui.show_history([e.to_dict() for e in entries])

@app.command()
def chat():
    """Interactive chat mode."""
    config = Config.load()
    chat_mode(config)

if __name__ == "__main__":
    app() 