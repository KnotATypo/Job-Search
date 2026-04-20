import logging
import os

progress_bars = os.getenv("PROGRESS_BARS", False)
logger = logging.getLogger("job-search")


def configure_logging(level=logging.INFO, fmt=None):
    if fmt is None:
        fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

    root = logging.getLogger()
    root.setLevel(os.getenv("LOG_LEVEL", level))

    # add stream handler if not already present
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(logging.Formatter(fmt))
        root.addHandler(stream_handler)

    # add file handler if not already present
    if not any(
        isinstance(h, logging.FileHandler) and h.baseFilename == os.path.abspath("job_search.log")
        for h in root.handlers
    ):
        file_handler = logging.FileHandler("job_search.log", encoding="utf-8")
        file_handler.setFormatter(logging.Formatter(fmt))
        root.addHandler(file_handler)

    return logger
