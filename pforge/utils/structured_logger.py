import logging
import orjson
from datetime import datetime

class JSONFormatter(logging.Formatter):
    """
    Formats log records as JSON strings.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_object = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
            "name": record.name,
        }

        # Add extra fields from the log record
        if hasattr(record, "extra_info"):
            log_object.update(record.extra_info)

        return orjson.dumps(log_object).decode("utf-8")

def get_structured_logger(name: str, level=logging.INFO) -> logging.Logger:
    """
    Returns a logger configured with the JSONFormatter.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Prevent duplicate logs if the logger is already configured
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = JSONFormatter()
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
