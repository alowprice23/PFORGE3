import typer
import asyncio
import logging
from pathlib import Path
from fakeredis import aioredis

from pforge.agents.observer_agent import ObserverAgent
from pforge.agents.planner_agent import PlannerAgent
from pforge.agents.fixer_agent import FixerAgent
from pforge.orchestrator.state_bus import StateBus, PuzzleState
from pforge.orchestrator.efficiency_engine import EfficiencyEngine

app = typer.Typer(
    name="doctor",
    help="Runs the end-to-end diagnosis and repair workflow on a project.",
)

logger = logging.getLogger(__name__)

async def run_doctor_flow(project_path: Path):
    """Simulates the agentic workflow for the doctor command."""

    typer.echo(f"🩺 Starting pForge Doctor on: {project_path}")

    redis_client = aioredis.FakeRedis(decode_responses=False)
    state_bus = StateBus(redis_client=redis_client) # type: ignore
    efficiency_engine = EfficiencyEngine(constants={})

    initial_state = PuzzleState(total_issues=1, total_tests=1)
    await state_bus.publish_update(initial_state)

    observer = ObserverAgent(state_bus, efficiency_engine, source_root=project_path)
    planner = PlannerAgent(state_bus, efficiency_engine)
    fixer = FixerAgent(state_bus, efficiency_engine)

    typer.echo("-> ObserverAgent is starting...")
    observer.start()
    await asyncio.sleep(1) # Give it a moment to run

    typer.echo("-> PlannerAgent is starting...")
    planner.start()
    await asyncio.sleep(1)

    typer.echo("-> FixerAgent is starting...")
    fixer.start()

    # Wait for the 'FIX_PATCH_APPLIED' event from the FixerAgent.
    # This is a more robust way to wait than a simple sleep.
    typer.echo("-> Waiting for fix to be applied...")
    fix_applied = False
    for _ in range(10): # Timeout after 10 seconds
        # We read the whole stream. Inefficient, but simple and fine for this.
        messages = await redis_client.xread(streams={"pforge:amp:global:events": "0-0"})
        if messages:
            for stream_name, stream_messages in messages:
                for message_id, message_data in stream_messages:
                    # The message is a JSON string stored in the 'amp_json' field.
                    # We check for the event type as a substring.
                    if b'FIX_PATCH_APPLIED' in message_data.get(b'amp_json', b''):
                        fix_applied = True
                        break
            if fix_applied:
                break
        if fix_applied:
            break
        await asyncio.sleep(1)

    if not fix_applied:
        typer.echo("-> Timed out waiting for fix.")

    typer.echo("-> Stopping agents...")
    await observer.stop()
    await planner.stop()
    await fixer.stop()

    typer.echo("✅ Doctor workflow complete.")


@app.command()
def run(
    project_path: Path = typer.Argument(
        ...,
        help="The path to the project directory to be analyzed.",
        exists=True,
        file_okay=False,
        resolve_path=True,
    )
):
    """
    Analyzes a project, proposes a fix for a bug, and applies it.
    """
    try:
        asyncio.run(run_doctor_flow(project_path))
    except Exception as e:
        logger.error(f"An error occurred during the doctor workflow: {e}", exc_info=True)
        typer.echo(f"🚨 Error: {e}")
        raise typer.Exit(code=1)
