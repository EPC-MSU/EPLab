from typing import Dict
from copy import deepcopy
import json


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


class ShortFloatCustomJSONEncoder(json.JSONEncoder):
    def __init__(self, *_args, **_kwargs):
        super(ShortFloatCustomJSONEncoder, self).__init__(*_args, **_kwargs)
        self.current_indent = 0
        self.current_indent_str = ""

    def encode(self, o):
        # Recursive Processing for lists required
        if isinstance(o, (list, tuple)):
            primitives_only = True
            for item in o:
                if isinstance(item, (list, tuple, dict)):
                    primitives_only = False
                    break
            output = []
            if primitives_only:
                for item in o:
                    output.append(json.dumps(item))
                return "[ " + ", ".join(output) + " ]"
            else:
                self.current_indent += self.indent
                self.current_indent_str = "".join([" " for _ in range(self.current_indent)])
                for item in o:
                    output.append(self.current_indent_str + self.encode(item))
                self.current_indent -= self.indent
                self.current_indent_str = "".join([" " for _ in range(self.current_indent)])
                return "[\n" + ",\n".join(output) + "\n" + self.current_indent_str + "]"
        # Recursive Processing for dictionaries required
        elif isinstance(o, dict):
            output = []
            self.current_indent += self.indent
            self.current_indent_str = "".join([" " for _ in range(self.current_indent)])
            for key, value in o.items():
                output.append(self.current_indent_str + json.dumps(key) + ": " + self.encode(value))
            self.current_indent -= self.indent
            self.current_indent_str = "".join([" " for _ in range(self.current_indent)])
            return "{\n" + ",\n".join(output) + "\n" + self.current_indent_str + "}"
        # Special float processing
        elif isinstance(o, float):
            return format(o, '.3g')
        else:
            return json.dumps(o)


if __name__ == "__main__":
    from jsonschema.validators import validate
    from argparse import ArgumentParser

    parser = ArgumentParser(description="Convert EyePoint P10 format to EPLab format")
    parser.add_argument("--source", help="EyePoint P10 elements.json file", default="elements.json")
    parser.add_argument("--destination", help="EPLab output json file", default="converted.json")
    parser.add_argument("--validate", help="Validate output file over this schema, optional parameter",
                        nargs='?', const="doc/elements.schema.json")

    args = parser.parse_args()

    with open(args.source, "r") as source_file:
        converted = convert_p10(json.load(source_file), "0.0.0")

    with open(args.destination, "w") as dest_file:
        dest_file.write(json.dumps(converted, indent=0, cls=ShortFloatCustomJSONEncoder))

    if args.validate is not None:
        with open(args.validate) as schema:
            validate(converted, json.load(schema))
