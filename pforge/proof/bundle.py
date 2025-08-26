from __future__ import annotations
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from pforge.orchestrator.signals import ProofObligation

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


def assemble_proof_bundle(
    tree_sha: str,
    venv_lock_sha: str,
    constraints: List[ProofObligation],
    test_results: Optional[Dict[str, Any]] = None,
    metrics_snapshot: Optional[Dict[str, Any]] = None,
    plan_details: Optional[Dict[str, Any]] = None,
    effort_metrics: Optional[Dict[str, Any]] = None,
    is_qed: bool = False
) -> ProofBundle:
    """
    A builder function to construct a valid ProofBundle from various evidence sources.

    This function ensures that a bundle is created in a consistent and validated manner.
    """

    # In a real implementation, we might add more validation here to ensure
    # that the inputs are well-formed before creating the bundle.

    bundle = ProofBundle(
        tree_sha=tree_sha,
        venv_lock_sha=venv_lock_sha,
        constraints=constraints,
        tests=test_results,
        metrics=metrics_snapshot,
        planner=plan_details,
        effort=effort_metrics,
        qed=is_qed
    )

    return bundle
