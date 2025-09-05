import asyncio
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch, AsyncMock
import orjson

import pytest
import fakeredis.aioredis

from pforge.orchestrator.core import Orchestrator
from pforge.orchestrator.signals import Message, MsgType
from pforge.config import Config
from pforge.project import Project
from pforge.agents.misfit_agent import MisfitAgent


class FakeMisfitLLM:
    def __init__(self, *args, **kwargs):
        pass

    async def chat(self, *args, **kwargs):
        verdict = {
            "misfit": True,
            "suggestion": "utils/helpers.py"
        }
        return orjson.dumps(verdict)


@pytest.fixture
def refactoring_project():
    """Creates a temporary project for testing the refactoring loop."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)

        # Create pforge.yaml
        (project_dir / "pforge.yaml").write_text("doctor:\n  retry_limit: 1\n")

        # Create models/user.py with a misfit function
        models_dir = project_dir / "models"
        models_dir.mkdir()
        (models_dir / "user.py").write_text(
            "class User:\n"
            "    pass\n\n"
            "def is_valid_email(email: str) -> bool:\n"
            '    return "@" in email\n'
        )

        # Create services/registration.py which imports the misfit
        services_dir = project_dir / "services"
        services_dir.mkdir()
        (services_dir / "registration.py").write_text(
            "from models.user import is_valid_email\n\n"
            "def register_user(email: str):\n"
            "    if is_valid_email(email):\n"
            '        print("User registered")\n'
        )

        # Create utils/helpers.py as the target for the refactoring
        utils_dir = project_dir / "utils"
        utils_dir.mkdir()
        (utils_dir / "helpers.py").touch()

        yield project_dir


@pytest.mark.asyncio
async def test_auto_refactoring_loop(refactoring_project):
    """
    Tests the full Misfit -> Planner -> Fixer refactoring loop.
    """
    project_dir = refactoring_project

    with patch("pforge.agents.misfit_agent.OpenAIClient", new=FakeMisfitLLM), \
         patch("redis.asyncio.from_url", return_value=fakeredis.aioredis.FakeRedis()), \
         patch("pforge.orchestrator.core.Orchestrator._handle_spec_checked", new_callable=AsyncMock):

        # --- Setup Orchestrator ---
        config = Config.load(project_dir / "pforge.yaml")
        project = Project(project_dir)
        orchestrator = Orchestrator(config, project)
        orchestrator.setup_agents()

        # --- Trigger the MisfitAgent ---
        initial_message = Message(
            type=MsgType.FIX_PATCH_APPLIED,
            payload={"file_path": "models/user.py"}
        )
        await orchestrator.bus.publish(MsgType.FIX_PATCH_APPLIED.value, initial_message)

        # --- Run the orchestrator ---
        try:
            await orchestrator.run(timeout=15.0)
        finally:
            orchestrator.stop()

        # --- Assertions ---
        user_model_content = (project_dir / "models/user.py").read_text()
        assert "def is_valid_email" not in user_model_content

        helpers_content = (project_dir / "utils/helpers.py").read_text()
        assert "def is_valid_email" in helpers_content

        registration_service_content = (project_dir / "services/registration.py").read_text()
        assert "from utils.helpers import is_valid_email" in registration_service_content
        assert "from models.user import is_valid_email" not in registration_service_content
