from __future__ import annotations
import typer
import orjson
from typing import Optional

# This CLI is part of the main `pforge` app, but we define its logic here.
# It would be registered in `cli/main.py`.

app = typer.Typer(help="Tools for backtesting and verifying pForge proofs.")

@app.command()
def verify(
    amp_log_file: typer.FileText = typer.Option(
        ...,
        "--session",
        "-s",
        help="Path to the AMP event log file for the session to verify."
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Print detailed discrepancies."),
):
    """
    Verifies the integrity and correctness of a past pForge session.

    This command reads an AMP event log, and for every proof-carrying event,
    it re-runs the validation checks to ensure the proof was honest.
    """
    from .verifier import verify_proof_bundle, VerificationResult
    from .bundle import ProofBundle

    typer.echo(f"Verifying session from log file: {amp_log_file.name}")

    verified_count = 0
    failed_count = 0

    for line in amp_log_file:
        try:
            amp_event_dict = orjson.loads(line)

            # We only care about events that carry a proof bundle
            if "proof" not in amp_event_dict or not amp_event_dict["proof"]:
                continue

            # Reconstruct the objects needed for verification
            # In a real system, you'd have a more robust way to get the signature
            # and the canonical JSON string that was signed.
            # Here, we'll assume the log contains enough info or we re-serialize.
            proof = ProofBundle(**amp_event_dict["proof"])

            # This is a simplification. The signature is on the canonical string,
            # which we would need to reconstruct perfectly.
            amp_event_json_for_signing = orjson.dumps(amp_event_dict, option=orjson.OPT_SORT_KEYS)
            amp_event_sig = amp_event_dict.get("sig", "")

            typer.echo(f"  Verifying proof from event op_id: {amp_event_dict.get('op_id')}...")

            # This is where the magic happens
            result: VerificationResult = verify_proof_bundle(proof, amp_event_json_for_signing, amp_event_sig)

            if result.is_valid:
                verified_count += 1
                typer.secho("    ✅ Verification successful.", fg=typer.colors.GREEN)
            else:
                failed_count += 1
                typer.secho("    ❌ Verification FAILED.", fg=typer.colors.RED)
                if verbose:
                    for issue in result.discrepancies:
                        typer.secho(f"       - {issue}", fg=typer.colors.YELLOW)

        except (orjson.JSONDecodeError, KeyError) as e:
            typer.secho(f"Skipping malformed line in log: {e}", fg=typer.colors.RED)
            continue

    typer.echo("\n" + "="*30)
    typer.echo("Verification Summary:")
    typer.secho(f"  Proofs Verified: {verified_count}", fg=typer.colors.GREEN)
    typer.secho(f"  Proofs Failed:   {failed_count}", fg=typer.colors.RED if failed_count > 0 else typer.colors.GREEN)
    typer.echo("="*30)

    if failed_count > 0:
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()
