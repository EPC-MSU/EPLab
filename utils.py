import json
from typing import Optional, Dict


def read_json(path: Optional[str] = None) -> Optional[Dict]:
    if not path:
        return None

    with open(path, "r") as file:
        return json.load(file)
