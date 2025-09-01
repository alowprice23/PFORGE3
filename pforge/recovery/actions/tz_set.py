from __future__ import annotations
import os
import time

def set_timezone_to_utc() -> dict:
    """
    Sets the current process's timezone to UTC.

    This is achieved by setting the 'TZ' environment variable and then
    calling time.tzset() to apply the change.

    Returns:
        A dictionary containing a proof of the action taken.
    """
    try:
        os.environ["TZ"] = "UTC"
        # time.tzset() is not available on Windows, but setting TZ works.
        if hasattr(time, "tzset"):
            time.tzset()

        proof = {
            "action": "set_timezone_to_utc",
            "status": "success",
            "new_timezone": time.tzname[0],
        }
        return proof
    except Exception as e:
        return {"action": "set_timezone_to_utc", "status": "error", "error": str(e)}
