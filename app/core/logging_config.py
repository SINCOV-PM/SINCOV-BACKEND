# app/core/logging_config.py
import logging
import sys

def setup_logging(level: str = "INFO"):
    """
    Configures global logging for the entire application.
    Logs to stdout (container-friendly) and includes timestamps.
    """
    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=log_format,
        handlers=[logging.StreamHandler(sys.stdout)],  # ensures logs go to console
    )

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)

    logging.getLogger(__name__).info("Global logging configured.")
