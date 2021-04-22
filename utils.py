import json
from typing import Optional, Dict


def read_json(path: Optional[str] = None) -> Optional[Dict]:
    if not path:
        return None

    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)
