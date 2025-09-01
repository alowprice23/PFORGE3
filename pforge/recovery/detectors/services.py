from __future__ import annotations
from typing import Tuple
import os
import importlib

def check_redis_availability(
    host: str | None = None, port: int | None = None
) -> Tuple[bool, dict]:
    """
    Probes for the availability of a Redis service.

    It first tries to connect to a real Redis server using the provided
    host and port, or from environment variables (REDIS_HOST, REDIS_PORT).
    If that fails, it checks if the 'fakeredis' library is available as a
    fallback for local testing.
    """
    redis_host = host or os.environ.get("REDIS_HOST", "127.0.0.1")
    redis_port = port or int(os.environ.get("REDIS_PORT", 6379))

    try:
        # Lazy import redis to avoid dependency if not used.
        import redis
        r = redis.Redis(host=redis_host, port=redis_port, socket_connect_timeout=1)
        if r.ping():
            return True, {"status": "connected", "host": redis_host, "port": redis_port}
    except ImportError:
        # If redis library isn't even installed, we can't connect.
        pass
    except redis.exceptions.ConnectionError as e:
        # This means we couldn't connect to a real redis.
        pass

    # If connecting to a real Redis fails, check for fakeredis.
    try:
        importlib.import_module("fakeredis")
        return True, {"status": "available", "type": "fakeredis"}
    except ImportError:
        return False, {"status": "unavailable", "host": redis_host, "port": redis_port}

    return False, {"status": "unavailable", "host": redis_host, "port": redis_port}
