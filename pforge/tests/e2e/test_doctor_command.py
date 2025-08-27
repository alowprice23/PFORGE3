from typer.testing import CliRunner
import os
import tempfile
import pytest

from pforge.cli.main import app
from pforge.llm_clients.openai_o3_client import OpenAIClient

runner = CliRunner()

def test_doctor_command_e2e(monkeypatch):
    """
    Tests the full end-to-end doctor command workflow.
    It creates a buggy file, runs the doctor, and asserts the file is fixed.
    """
    # 1. Mock the LLM response to avoid real API calls and provide a predictable fix.
    async def mock_generate(*args, **kwargs):
        # This is the expected full content of the file after the fix.
        fixed_content = "def buggy_function():\\n    return 'this is a fix'"
        return {
            "choices": [{"message": {"content": f"```python\\n{fixed_content}\\n```"}}]
        }
    monkeypatch.setattr(OpenAIClient, "generate", mock_generate)

    # 2. Setup the buggy project in a temporary directory.
    with tempfile.TemporaryDirectory() as tmpdir:
        buggy_file_path = os.path.join(tmpdir, "buggy_file.py")
        buggy_code = "def buggy_function():\\n    return 'this is a bug'"
        with open(buggy_file_path, "w") as f:
            f.write(buggy_code)

        # 3. Run the doctor command on the temporary project.
        result = runner.invoke(app, ["doctor", "run", tmpdir])

        # 4. Assert that the command ran successfully.
        assert result.exit_code == 0, f"CLI command failed with output: {result.stdout}"
        assert "Doctor workflow complete." in result.stdout

        # 5. Assert that the file was actually fixed.
        with open(buggy_file_path, "r") as f:
            fixed_code_from_file = f.read()

        expected_code = "def buggy_function():\\n    return 'this is a fix'"
        assert fixed_code_from_file.strip() == expected_code.strip()
