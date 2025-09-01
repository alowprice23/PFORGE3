from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import List, Dict, Any

# Import the other verifier functions from this module
from .precision_at_action import calculate_precision_at_action
from .escape_rate import calculate_escape_rate
from .conflict_minimality import verify_conflict_minimality
from .qed_gate_audit import audit_qed_gates

def generate_kpi_report(session_log: List[Dict[str, Any]]) -> str:
    """
    Generates a summary report of all the KPIs for a session.

    Args:
        session_log: A list of AMP events.

    Returns:
        A formatted string containing the KPI report.
    """
    # Calculate each KPI
    precision = calculate_precision_at_action(session_log)
    escape_rate = calculate_escape_rate(session_log)
    is_minimal, minimality_failures = verify_conflict_minimality(session_log)
    all_qeds_valid, qed_failures = audit_qed_gates(session_log)

    # Format the report
    report = []
    report.append("=" * 40)
    report.append("pForge Verification KPI Report")
    report.append("=" * 40)
    report.append(f"  Precision@Action: {precision:.2%}")
    report.append(f"  Targeted Test Escape Rate: {escape_rate:.2%}")
    report.append(f"  Conflict Minimality Check: {'PASSED' if is_minimal else 'FAILED'}")
    if minimality_failures:
        report.append(f"    - Found {len(minimality_failures)} non-minimal hitting sets.")
    report.append(f"  QED Gate Audit: {'PASSED' if all_qeds_valid else 'FAILED'}")
    if qed_failures:
        report.append(f"    - Found {len(qed_failures)} invalid QED events.")
    report.append("=" * 40)

    return "\n".join(report)

def main():
    """
    Command-line interface for the KPI report generator.
    """
    parser = argparse.ArgumentParser(
        description="Generate a KPI report from a pForge session log."
    )
    parser.add_argument(
        "session_log_file",
        type=Path,
        help="Path to the session log file (JSON format)."
    )
    args = parser.parse_args()

    if not args.session_log_file.exists():
        print(f"Error: File not found at {args.session_log_file}")
        return

    try:
        with open(args.session_log_file, 'r') as f:
            log_data = json.load(f)

        if not isinstance(log_data, list):
            print("Error: Session log must be a JSON array of events.")
            return

        report_str = generate_kpi_report(log_data)
        print(report_str)

    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in {args.session_log_file}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
