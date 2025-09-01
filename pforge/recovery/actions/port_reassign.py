from __future__ import annotations
import socket

def find_free_port() -> dict:
    """
    Finds a free port by binding a socket to port 0.

    The operating system will then assign an available ephemeral port.

    Returns:
        A dictionary containing a proof of the action, including the
        port that was found.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            # Binding to port 0 tells the OS to find and assign a free port.
            s.bind(("", 0))
            s.listen(1)
            port = s.getsockname()[1]
            proof = {
                "action": "find_free_port",
                "status": "success",
                "port": port,
            }
            return proof
    except Exception as e:
        return {"action": "find_free_port", "status": "error", "error": str(e)}
