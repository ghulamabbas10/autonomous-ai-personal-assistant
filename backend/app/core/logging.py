import logging
import logging.config

from pythonjsonlogger.json import JsonFormatter


def configure_logging(level: str) -> None:
    """Configure structured logs without ever serializing settings or secrets."""

    formatter = JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s",
        rename_fields={"levelname": "level", "asctime": "timestamp"},
    )
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
