import typer
from pathlib import Path

app = typer.Typer(
    name="init",
    help="Initializes a new pForge project by creating a configuration file.",
)

DEFAULT_CONFIG = """\
# pForge Project Configuration

[doctor]
# The number of times the FixerAgent should retry a failed fix.
retry_limit = 2

[llm]
# The default LLM provider to use for generating fixes.
# provider = "openai"

# [llm.providers.openai]
# model = "gpt-4-turbo-preview"

# [llm.providers.anthropic]
# model = "claude-3-opus-20240229"
"""

@app.callback(invoke_without_command=True)
def init(
    ctx: typer.Context,
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force overwrite of an existing pforge.toml file.",
    )
):
    """
    Creates a pforge.toml file in the current directory.
    """
    if ctx.invoked_subcommand is not None:
        return

    config_path = Path("pforge.toml")
    if config_path.exists() and not force:
        typer.echo("pforge.toml already exists. Use --force to overwrite.")
        raise typer.Exit(code=1)

    with open(config_path, "w") as f:
        f.write(DEFAULT_CONFIG)

    typer.echo(f"✅ Created pforge.toml in {config_path.resolve()}")
