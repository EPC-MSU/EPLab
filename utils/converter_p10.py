from typing import Dict
from copy import deepcopy


def _convert_measurement_settings(settings: Dict) -> Dict:
    remove_settings_keys = ["flags", "reserved", "n_charge_points", "n_points", "max_current"]
    rename_settings_keys = {
        "desc_frequency": "sampling_rate",
    }
    internal_resistance_map = {
        3: 475,
        2: 4750,
        1: 47500
    }

    settings["internal_resistance"] = internal_resistance_map.get(settings["flags"], 0)

    for key, new_key in rename_settings_keys.items():
        settings[new_key] = settings.pop(key)
    for key in remove_settings_keys:
        settings.pop(key, None)

    return settings


def _convert_ivc(ivc: Dict, is_reference: bool = False, is_dynamic: bool = False) -> Dict:
    new_ivc = {
        "measurement_settings": _convert_measurement_settings(ivc["measure_settings"]),
        "iv_array": []
    }
    if is_reference:
        ivc["is_reference"] = True
    if is_dynamic:
        ivc["is_dynamic"] = True

    for current, voltage in zip(ivc["current"], ivc["voltage"]):
        new_ivc["iv_array"].append({"current": current,
                                    "voltage": voltage})
    return new_ivc


def _convert_pin(pin: Dict) -> Dict:
    remove_pin_keys = ["score", "reference_ivc", "is_dynamic", "cluster_id"]

    is_dynamic = pin.get("is_dynamic", False)

    pin["ivc"] = [_convert_ivc(pin["ivc"], is_dynamic=is_dynamic)]
    if pin.get("reference_ivc", None):
        pin["ivc"].append(_convert_ivc(pin["reference_ivc"], is_reference=True, is_dynamic=is_dynamic))

    for key in remove_pin_keys:
        pin.pop(key, None)

    return pin


def _convert_element(element: Dict) -> Dict:
    remove_element_keys = ["side_indexes", "probability", "manual_name", "is_manual", "w_pins", "h_pins", "width",
                           "height"]

    element["pins"] = [_convert_pin(pin) for pin in element["pins"]]

    if not element["is_manual"]:
        element["set_automatically"] = True

    for key in remove_element_keys:
        element.pop(key, None)
    if not element.get("bounding_zone", True):
        element.pop("bounding_zone", None)

    return element


def convert_p10(source_json: Dict, version: str) -> Dict:
    result = deepcopy(source_json)

    result["elements"] = [_convert_element(element) for element in result["elements"]]

    if "version" not in result:
        result["version"] = version

    return result


if __name__ == "__main__":
    from jsonschema.validators import validate
    import json
    from argparse import ArgumentParser

    parser = ArgumentParser(description="Convert EyePoint P10 format to EPLab format")
    parser.add_argument("--source", help="EyePoint P10 elements.json file", default="elements.json")
    parser.add_argument("--destination", help="EPLab output json file", default="converted.json")
    parser.add_argument("--validate", help="Validate output file over this schema, optional parameter",
                        nargs="?", const="doc/elements.schema.json")

    args = parser.parse_args()

    with open(args.source, "r") as source_file:
        converted = convert_p10(json.load(source_file), "0.0.0")

    with open(args.destination, "w") as dest_file:
        dest_file.write(json.dumps(converted, indent=1, sort_keys=True))

    if args.validate is not None:
        with open(args.validate) as schema:
            validate(converted, json.load(schema))
