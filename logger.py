"""
File with logger.
"""

import logging

formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(module)s.%(funcName)s: %(message)s")
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
stream_handler.setLevel(logging.INFO)
logger = logging.getLogger("eplab")
logger.addHandler(stream_handler)
logger.setLevel(logging.INFO)
logger.propagate = False
