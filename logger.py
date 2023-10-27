"""
File with logger.
"""

import logging


def set_logger() -> None:
    formatter = logging.Formatter("[%(asctime)s %(levelname)s] %(message)s")
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(logging.INFO)
    logger = logging.getLogger("eplab")
    logger.addHandler(stream_handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
