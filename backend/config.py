import copy
import json
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = APP_DIR / "configs"
APP_CONFIG_PATH = CONFIG_DIR / "sidechick.json"
LEGACY_FIH_CONFIG_PATH = APP_DIR / "fih_config.json"
APP_VERSION = "v1.7.0"
UPDATE_REPO = "Beng420/sidechick"


APP_DEFAULT_CONFIG = {
    "config_version": 1,
    "selected_script": "fih",
    "theme": "dark",
}


FIH_DEFAULT_CONFIG = {
    "config_version": 3,
    "region": [1519, 724, 17, 50],
    "target_rgb": [252, 84, 84],
    "tolerance": 20.0,
    "screen_backend": "auto",
    "input_backend": "auto",
    "rod_slot": "4",
    "weapon_slot": "3",
    "orb_slot": "5",
    "poll_interval": 0.05,
    "scan_interval": 0.12,
    "action_gap": 0.03,
    "post_cycle_gap": 0.5,
    "min_wait_time": 10.0,
    "key_debounce": 0.25,
    "manual_input_debounce": 0.2,
    "script_input_ignore": 0.8,
    "orb_prepare_seconds": 50.0,
    "start_mode": "hype",
    "timer_mode_enabled": False,
    "orb_mode_enabled": False,
    "hotkeys_enabled": True,
    "hotkeys": {
        "stop": "f1",
        "pause": ["enter"],
        "timer_mode": "f4",
        "fishing_mode": "f6",
        "orb_mode": "f7",
        "manual_override_keys": ["1", "2", "3", "4", "5", "6", "7", "8", "9"],
        "manual_override_mouse_buttons": ["mouse:right"],
    },
}


SUPERPAIRS_DEFAULT_CONFIG = {
    "start_x": 801,
    "start_y": 391,
    "horizontal_gap": 36,
    "vertical_gap": 36,
    "columns": 9,
    "rows": 4,
    "target_colors": [[101, 168, 101], [123, 190, 123], [85, 255, 85]],
    "tolerance": 20,
    "scan_interval": 0.10,
    "click_cooldown": 0.10,
    "move_back_position": [700, 300],
    "toggle_hotkey": "f1",
    "hotkeys_enabled": True,
}


SCRIPT_DEFINITIONS = {
    "fih": {
        "id": "fih",
        "name": "FIh",
        "description": "Fishing helper",
        "script_path": APP_DIR / "fih.py",
        "config_path": CONFIG_DIR / "fih.json",
        "legacy_config_path": LEGACY_FIH_CONFIG_PATH,
        "stop_path": APP_DIR / "fih_stop.flag",
        "control_path": APP_DIR / "fih_control.json",
        "default_config": FIH_DEFAULT_CONFIG,
        "mode_status": True,
        "schema": [
            {
                "title": "General",
                "fields": [
                    {"key": "start_mode", "label": "Start mode", "type": "select", "options": ["trophy", "hype", "flay"]},
                    {"key": "screen_backend", "label": "Screen backend", "type": "select", "options": ["auto", "mss", "dxcam"]},
                    {"key": "input_backend", "label": "Input backend", "type": "select", "options": ["auto", "legacy", "pynput"]},
                    {"key": "timer_mode_enabled", "label": "Timer mode", "type": "bool"},
                    {"key": "orb_mode_enabled", "label": "Orb mode", "type": "bool"},
                    {"key": "hotkeys_enabled", "label": "Script hotkeys", "type": "bool"},
                ],
            },
            {
                "title": "Detection",
                "fields": [
                    {"key": "region.0", "label": "Region left", "type": "int"},
                    {"key": "region.1", "label": "Region top", "type": "int"},
                    {"key": "region.2", "label": "Region width", "type": "int"},
                    {"key": "region.3", "label": "Region height", "type": "int"},
                    {"key": "target_rgb.0", "label": "Target R", "type": "int"},
                    {"key": "target_rgb.1", "label": "Target G", "type": "int"},
                    {"key": "target_rgb.2", "label": "Target B", "type": "int"},
                    {"key": "tolerance", "label": "Tolerance", "type": "float"},
                ],
            },
            {
                "title": "Timing",
                "fields": [
                    {"key": "scan_interval", "label": "Scan interval", "type": "float"},
                    {"key": "action_gap", "label": "Action gap", "type": "float"},
                    {"key": "post_cycle_gap", "label": "Post cycle gap", "type": "float"},
                    {"key": "min_wait_time", "label": "Min wait time", "type": "float"},
                    {"key": "orb_prepare_seconds", "label": "Orb prepare seconds", "type": "float"},
                    {"key": "script_input_ignore", "label": "Script input ignore", "type": "float"},
                ],
            },
            {
                "title": "Hotkeys",
                "fields": [
                    {"key": "hotkeys.stop", "label": "Stop", "type": "binding"},
                    {"key": "hotkeys.pause", "label": "Pause", "type": "bindings"},
                    {"key": "hotkeys.timer_mode", "label": "Timer mode", "type": "binding"},
                    {"key": "hotkeys.fishing_mode", "label": "Fishing mode", "type": "binding"},
                    {"key": "hotkeys.orb_mode", "label": "Orb mode", "type": "binding"},
                    {"key": "hotkeys.manual_override_keys", "label": "Manual keys", "type": "bindings"},
                    {"key": "hotkeys.manual_override_mouse_buttons", "label": "Manual mouse buttons", "type": "bindings"},
                ],
            },
            {
                "title": "Slots",
                "fields": [
                    {"key": "rod_slot", "label": "Rod slot", "type": "text"},
                    {"key": "weapon_slot", "label": "Weapon slot", "type": "text"},
                    {"key": "orb_slot", "label": "Orb slot", "type": "text"},
                ],
            },
        ],
    },
    "superpairs": {
        "id": "superpairs",
        "name": "Superpairs",
        "description": "Superpairs board helper",
        "script_path": APP_DIR / "superpairs.py",
        "config_path": CONFIG_DIR / "superpairs.json",
        "legacy_config_path": None,
        "stop_path": APP_DIR / "superpairs_stop.flag",
        "control_path": APP_DIR / "superpairs_control.json",
        "default_config": SUPERPAIRS_DEFAULT_CONFIG,
        "mode_status": False,
        "schema": [
            {
                "title": "Grid",
                "fields": [
                    {"key": "start_x", "label": "Start X", "type": "int"},
                    {"key": "start_y", "label": "Start Y", "type": "int"},
                    {"key": "horizontal_gap", "label": "Horizontal gap", "type": "int"},
                    {"key": "vertical_gap", "label": "Vertical gap", "type": "int"},
                    {"key": "columns", "label": "Columns", "type": "int"},
                    {"key": "rows", "label": "Rows", "type": "int"},
                ],
            },
            {
                "title": "Detection",
                "fields": [
                    {"key": "target_colors", "label": "Target colors", "type": "json"},
                    {"key": "tolerance", "label": "Tolerance", "type": "int"},
                    {"key": "scan_interval", "label": "Scan interval", "type": "float"},
                    {"key": "click_cooldown", "label": "Click cooldown", "type": "float"},
                    {"key": "move_back_position", "label": "Move-back position", "type": "json"},
                ],
            },
            {
                "title": "Hotkeys",
                "fields": [
                    {"key": "toggle_hotkey", "label": "Pause/resume", "type": "binding"},
                    {"key": "hotkeys_enabled", "label": "Script hotkeys", "type": "bool"},
                ],
            },
        ],
    },
}


def merge_defaults(defaults, loaded):
    result = copy.deepcopy(defaults)
    if not isinstance(loaded, dict):
        return result
    for key, value in loaded.items():
        if key not in result:
            continue
        if isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_defaults(result[key], value)
        else:
            result[key] = value
    return result


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def load_app_config():
    loaded = read_json(APP_CONFIG_PATH) if APP_CONFIG_PATH.exists() else {}
    config = merge_defaults(APP_DEFAULT_CONFIG, loaded)
    if config["selected_script"] not in SCRIPT_DEFINITIONS:
        config["selected_script"] = "fih"
    write_json(APP_CONFIG_PATH, config)
    return config


def save_app_config(config):
    data = merge_defaults(APP_DEFAULT_CONFIG, config)
    write_json(APP_CONFIG_PATH, data)
    return data


def load_script_config(script_id):
    script = SCRIPT_DEFINITIONS[script_id]
    path = script["config_path"]
    loaded = {}
    if path.exists():
        loaded = read_json(path)
    elif script.get("legacy_config_path") and script["legacy_config_path"].exists():
        loaded = read_json(script["legacy_config_path"])

    config = merge_defaults(script["default_config"], loaded)
    write_json(path, config)
    return config


def save_script_config(script_id, config):
    script = SCRIPT_DEFINITIONS[script_id]
    data = merge_defaults(script["default_config"], config)
    write_json(script["config_path"], data)
    return data


def public_script(script_id):
    script = SCRIPT_DEFINITIONS[script_id]
    return {
        "id": script_id,
        "name": script["name"],
        "description": script["description"],
        "available": script["script_path"].exists(),
        "mode_status": script["mode_status"],
        "schema": script["schema"],
    }
