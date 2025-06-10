"""
File with logger.
"""

import logging
from typing import Optional


def get_file_handler(filename: str, formatter: logging.Formatter) -> logging.FileHandler:
    """
    :param filename: name of file for logging;
    :param formatter: formatter.
    :return: logging file handler.
    """

    file_handler = logging.FileHandler(filename)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    return file_handler


def get_stream_handler(formatter: logging.Formatter) -> logging.StreamHandler:
    """
    :param formatter: formatter.
    :return: logging stream handler.
    """

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(logging.INFO)
    return stream_handler


def set_logger(filename: Optional[str] = None) -> None:
    """
    :param filename: name of file for logging.
    """

    formatter = logging.Formatter("[%(asctime)s %(levelname)s] %(message)s")

    logger = logging.getLogger("eplab")
    logger.addHandler(get_stream_handler(formatter))
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    if filename:
        logger.addHandler(get_file_handler(filename, formatter))
