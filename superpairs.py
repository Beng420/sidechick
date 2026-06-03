import json
import time
from pathlib import Path

import mss
import numpy as np
import pyautogui

try:
    import keyboard
except ImportError:
    keyboard = None


pyautogui.PAUSE = 0

STOP_PATH = Path(__file__).with_name("superpairs_stop.flag")
CONTROL_PATH = Path(__file__).with_name("superpairs_control.json")
CONFIG_PATH = Path(__file__).with_name("configs") / "superpairs.json"

running = True
active = True
last_control_mtime = 0
hotkey_handle = None

DEFAULT_CONFIG = {
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


def merge_defaults(defaults, loaded):
    result = defaults.copy()
    for key, value in loaded.items():
        if key in result:
            result[key] = value
    return result


def load_config():
    if not CONFIG_PATH.exists():
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(json.dumps(DEFAULT_CONFIG, indent=2) + "\n", encoding="utf-8")
        return DEFAULT_CONFIG.copy()

    try:
        loaded = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        loaded = {}

    config = merge_defaults(DEFAULT_CONFIG, loaded)
    CONFIG_PATH.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    return config


def build_positions(config):
    start_x = int(config["start_x"])
    start_y = int(config["start_y"])
    horizontal_gap = int(config["horizontal_gap"])
    vertical_gap = int(config["vertical_gap"])
    columns = int(config["columns"])
    rows = int(config["rows"])
    return [
        (start_x + column * horizontal_gap, start_y + row * vertical_gap)
        for row in range(rows)
        for column in range(columns)
    ]


CONFIG = load_config()
POSITIONS = build_positions(CONFIG)
TARGET_COLORS = [tuple(color) for color in CONFIG["target_colors"]]
TOLERANCE = int(CONFIG["tolerance"])
SCAN_INTERVAL = float(CONFIG["scan_interval"])
CLICK_COOLDOWN = float(CONFIG["click_cooldown"])
MOVE_BACK_POSITION = tuple(CONFIG["move_back_position"])
last_click_time = 0.0


def color_matches(pixel_rgb, target_rgb):
    return all(abs(pixel - target) <= TOLERANCE for pixel, target in zip(pixel_rgb, target_rgb))


def scan_and_click(sct):
    global last_click_time

    if not running or not active:
        return False

    monitor = sct.monitors[1]
    frame = np.asarray(sct.grab(monitor))

    for x, y in POSITIONS:
        if not running or not active:
            return False

        if not (0 <= y < frame.shape[0] and 0 <= x < frame.shape[1]):
            continue

        b, g, r, _a = frame[y, x]
        pixel_rgb = (int(r), int(g), int(b))

        if any(color_matches(pixel_rgb, target) for target in TARGET_COLORS):
            now = time.monotonic()
            remaining_cooldown = CLICK_COOLDOWN - (now - last_click_time)
            if remaining_cooldown > 0:
                time.sleep(remaining_cooldown)

            print(f"Match at {(x, y)}. Clicking.", flush=True)
            pyautogui.click(x, y)
            last_click_time = time.monotonic()
            pyautogui.moveTo(*MOVE_BACK_POSITION)
            return True

    return False


def toggle_active():
    global active
    set_active(not active)


def set_active(enabled):
    global active
    if active == enabled:
        return
    active = enabled
    state = "running" if active else "paused"
    print(f"Superpairs {state}.", flush=True)


def request_stop():
    global running
    running = False
    print("Stopping Superpairs...", flush=True)


def handle_control_file():
    global last_control_mtime, CLICK_COOLDOWN, SCAN_INTERVAL

    if not CONTROL_PATH.exists():
        return

    try:
        stat = CONTROL_PATH.stat()
    except OSError:
        return

    if stat.st_mtime_ns == last_control_mtime:
        return
    last_control_mtime = stat.st_mtime_ns

    try:
        data = json.loads(CONTROL_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return

    command = data.get("command")
    if command == "stop":
        request_stop()
    elif command == "pause":
        set_active(False)
    elif command == "resume":
        set_active(True)
    elif command == "toggle_pause":
        toggle_active()
    elif command == "set_click_cooldown":
        CLICK_COOLDOWN = max(0.0, float(data.get("seconds", CLICK_COOLDOWN)))
        print(f"Click cooldown set to {CLICK_COOLDOWN:.3f}s.", flush=True)
    elif command == "set_scan_interval":
        SCAN_INTERVAL = max(0.01, float(data.get("seconds", SCAN_INTERVAL)))
        print(f"Scan interval set to {SCAN_INTERVAL:.3f}s.", flush=True)
    elif command == "set_runtime_state":
        if "paused" in data:
            set_active(not bool(data.get("paused")))
        if "hotkeys_enabled" in data:
            set_hotkeys_enabled(bool(data.get("hotkeys_enabled")))
    elif command == "set_hotkeys_enabled":
        set_hotkeys_enabled(bool(data.get("enabled")))


def set_hotkeys_enabled(enabled):
    global hotkey_handle

    CONFIG["hotkeys_enabled"] = bool(enabled)
    if keyboard is None:
        if enabled:
            print("keyboard package not available. Use Sidechick controls.", flush=True)
        return

    if enabled and hotkey_handle is None:
        hotkey = str(CONFIG["toggle_hotkey"]).strip() or "f1"
        hotkey_handle = keyboard.add_hotkey(hotkey, toggle_active)
        print(f"{hotkey} toggles Superpairs pause/resume.", flush=True)
        return

    if not enabled and hotkey_handle is not None:
        keyboard.remove_hotkey(hotkey_handle)
        hotkey_handle = None
        print("Script hotkeys disabled. Use Sidechick controls.", flush=True)


def install_hotkeys():
    set_hotkeys_enabled(CONFIG.get("hotkeys_enabled", True))


def main():
    STOP_PATH.unlink(missing_ok=True)
    CONTROL_PATH.unlink(missing_ok=True)
    install_hotkeys()
    print("Superpairs started.", flush=True)

    try:
        with mss.mss() as sct:
            while running:
                if STOP_PATH.exists():
                    request_stop()
                    break
                handle_control_file()
                if active:
                    scan_and_click(sct)
                time.sleep(SCAN_INTERVAL)
    finally:
        STOP_PATH.unlink(missing_ok=True)
        CONTROL_PATH.unlink(missing_ok=True)
        print("Superpairs stopped.", flush=True)


if __name__ == "__main__":
    main()
