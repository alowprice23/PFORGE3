from __future__ import annotations
import socket
from typing import Tuple

def check_port_collision(port: int, host: str = "127.0.0.1") -> Tuple[bool, dict]:
    """
    Checks for a port collision on a given port by trying to bind a socket.

    Args:
        port: The port number to check.
        host: The host to check on (defaults to localhost).

    Returns:
        A tuple where the first element is False if the port is in use (a
        collision), and True if it is free. The second element is a
        dictionary with details.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            # If bind succeeds, the port is free.
            is_free = True
            witness = {"status": "free", "port": port}
        except OSError as e:
            # EADDRINUSE means the port is already taken.
            if e.errno == socket.errno.EADDRINUSE:
                is_free = False
                witness = {"status": "in_use", "port": port}
            else:
                # Another OS error occurred.
                is_free = False
                witness = {"status": "error", "port": port, "error": str(e)}
    # The check returns True if the port is NOT in collision (i.e., is free).
    return is_free, witness
