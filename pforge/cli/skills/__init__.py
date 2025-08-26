"""
This package contains the implementation of each discrete "skill" or
subcommand that the pForge CLI can execute.

Each module in this package should define a `typer.Typer()` application object
named `app`, which will be dynamically discovered and registered by the
main CLI application in `cli/main.py`.
"""

from . import status
from . import proofs
from . import preflight
# ... other skills will be imported here as they are created.

__all__ = ["status", "proofs", "preflight"]
