import typer
import asyncio
import logging
from pathlib import Path
import orjson

from pforge.agents.observer_agent import ObserverAgent
from pforge.agents.planner_agent import PlannerAgent
from pforge.agents.fixer_agent import FixerAgent
from pforge.orchestrator.state_bus import StateBus, PuzzleState
from pforge.orchestrator.efficiency_engine import EfficiencyEngine
from pforge.messaging.in_memory_bus import InMemoryBus
from pforge.messaging.amp import AMPMessage

app = typer.Typer(
    name="doctor",
    help="Runs the end-to-end diagnosis and repair workflow on a project.",
)

logger = logging.getLogger(__name__)

async def run_doctor_flow(project_path: Path):
    """Simulates the agentic workflow for the doctor command."""

    typer.echo(f"🩺 Starting pForge Doctor on: {project_path}")

    bus = InMemoryBus()
    state_bus = StateBus(bus=bus)
    efficiency_engine = EfficiencyEngine(constants={})

    initial_state = PuzzleState(total_issues=1, total_tests=1)
    await state_bus.publish_update(initial_state)

    observer = ObserverAgent(state_bus, efficiency_engine, source_root=project_path)
    planner = PlannerAgent(state_bus, efficiency_engine)
    fixer = FixerAgent(state_bus, efficiency_engine, source_root=project_path)

    typer.echo("-> ObserverAgent is starting...")
    observer.start()
    await asyncio.sleep(1)

    typer.echo("-> PlannerAgent is starting...")
    planner.start()
    await asyncio.sleep(1)

    typer.echo("-> FixerAgent is starting...")
    fixer.start()
    await asyncio.sleep(1)

    typer.echo("-> Waiting for fix to be applied...")
    fix_event = None
    for _ in range(15): # Timeout after 15 seconds
        try:
            message: AMPMessage = await asyncio.wait_for(bus.get_queue("pforge:amp:global:events").get(), timeout=1.0)
            if message.type in ("FIX.PATCH_APPLIED", "FIX.PATCH_REJECTED"):
                fix_event = message
                break
        except asyncio.TimeoutError:
            pass

    if fix_event:
        typer.echo(f"-> FixerAgent finished with event: {fix_event.type}")
        if fix_event.type == "FIX.PATCH_REJECTED":
             typer.echo("-> Fix was rejected. See logs for details.")
    else:
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
