import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")

DEFAULTS = {
    "connection": {
        "mode": "usb",
        "com_port": "COM3",
        "baud_rate": "115200",
        "device_name": "EXO-01",
        "pairing_pin": "0000",
        "trigger_enabled": False,
    },
    "calibration": {
        "min": None,
        "max": None,
    },
    "trial": {
        "controller": "0",
        "stance": "20",
        "swing": "35",
        "estim": False,
    },
}


def load_config():
    if not os.path.exists(CONFIG_PATH):
        return json.loads(json.dumps(DEFAULTS))  # deep copy

    try:
        with open(CONFIG_PATH, "r") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return json.loads(json.dumps(DEFAULTS))

    merged = json.loads(json.dumps(DEFAULTS))
    for section, values in data.items():
        if section in merged and isinstance(values, dict):
            merged[section].update(values)
    return merged


def save_config(config):
    try:
        with open(CONFIG_PATH, "w") as f:
            json.dump(config, f, indent=2)
    except OSError:
        pass
