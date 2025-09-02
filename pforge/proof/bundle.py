from __future__ import annotations
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class ProofObligation(BaseModel):
    """Represents the result of checking a single formal constraint (φ)."""
    id: str = Field(..., description="The unique identifier of the constraint (e.g., 'lint.ruff.I001').")
    ok: Optional[bool] = Field(None, description="True if the constraint is satisfied, False if violated.")
    witness: Optional[Dict[str, Any]] = Field(None, description="Evidence for the outcome (e.g., linter output, test failure details).")

class ProofBundle(BaseModel):
    """
    A canonical, verifiable artifact that bundles all evidence related to a
    specific claim (e.g., a patch being applied, a specification being met).

    This object is designed to be self-contained and cryptographically signed,
    forming the basis of the "Proof or It Didn't Happen" principle.
    """

    # The exact state of the code this proof applies to.
    tree_sha: str = Field(..., description="The SHA256 hash of the code tree manifest (from CAS).")

    # The exact environment in which the proof was generated.
    venv_lock_sha: str = Field(..., description="A hash of the environment lockfile (e.g., requirements.txt or poetry.lock).")

    # The set of formal constraints checked.
    constraints: List[ProofObligation] = Field(default_factory=list, description="A list of checks against the system's specification (Φ).")

    # Evidence from test runs.
    tests: Optional[Dict[str, Any]] = Field(None, description="Results from the test runner, including exit codes and report hashes.")

    # A snapshot of key system metrics at the time of the proof.
    metrics: Optional[Dict[str, Any]] = Field(None, description="A snapshot of E, H, and other key performance indicators.")

    # Data from the planner, if this proof relates to a planned action.
    planner: Optional[Dict[str, Any]] = Field(None, description="Details of the plan, including objective score and chosen actions.")

    # The measured cost of the operation.
    effort: Optional[Dict[str, Any]] = Field(None, description="The measured effort, e.g., edit distance or execution time.")

    # The final "Quality-Ensure-Done" flag.
    # This is only set to True on the final proof of a successful run.
    qed: bool = Field(default=False, description="The 'Quod Erat Demonstrandum' flag, marking a final, verified success.")

    # --- FixerAgent specific fields ---
    file_path: Optional[str] = Field(None, description="The path to the file that was modified.")
    content_sha_before: Optional[str] = Field(None, description="The SHA256 hash of the file content before the fix.")
    content_sha_after: Optional[str] = Field(None, description="The SHA256 hash of the file content after the fix.")
    llm_prompt: Optional[str] = Field(None, description="The prompt sent to the LLM.")
    llm_response: Optional[str] = Field(None, description="The response received from the LLM.")
