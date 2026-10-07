import logging
from pathlib import Path

def setup_logging(log_path: str = "output/generation.log") -> logging.Logger:
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("starglob_datalab")
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    console_handler = logging.StreamHandler()
    console_handler.stream.reconfigure(encoding="utf-8")

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger