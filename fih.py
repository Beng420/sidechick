import json
import platform
import sys
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from threading import RLock
from typing import Callable

try:
    import mss
    import numpy as np
    import pyautogui
except ImportError as exc:
    missing_package = exc.name or "ein benoetigtes Paket"
    raise SystemExit(
        f"Fehlendes Python-Paket: {missing_package}\n"
        "Installiere die Abhaengigkeiten im Script-Ordner mit:\n"
        "  python3 -m pip install -r requirements.txt\n"
        "oder auf Windows:\n"
        "  py -m pip install -r requirements.txt"
    ) from exc

try:
    import dxcam
except ImportError:
    dxcam = None

try:
    from pynput import keyboard as pynput_keyboard
    from pynput import mouse as pynput_mouse
except ImportError:
    pynput_keyboard = None
    pynput_mouse = None

try:
    import keyboard as legacy_keyboard
    import mouse as legacy_mouse
except ImportError:
    legacy_keyboard = None
    legacy_mouse = None

pyautogui.PAUSE = 0

CURRENT_CONFIG_VERSION = 5
FAST_ACTION_GAP = 0.10
PAUSE_KEY_DEBOUNCE = 0.06
MOUSE_BUTTON_ALIASES = {
    "left": "left",
    "mouse:left": "left",
    "mouse1": "left",
    "right": "right",
    "mouse:right": "right",
    "mouse2": "right",
    "middle": "middle",
    "mouse:middle": "middle",
    "mouse3": "middle",
    "x": "x",
    "mouse:x": "x",
    "x1": "x",
    "mouse4": "x",
    "x2": "x2",
    "mouse:x2": "x2",
    "mouse5": "x2",
}
PUNCTUATION_KEY_ALIASES = {
    ",": "comma",
    "comma": "comma",
    "-": "minus",
    "minus": "minus",
    ".": "period",
    "period": "period",
    "dot": "period",
    "/": "slash",
    "slash": "slash",
    "\\": "backslash",
    "backslash": "backslash",
    ";": "semicolon",
    "semicolon": "semicolon",
    "'": "apostrophe",
    "apostrophe": "apostrophe",
    "quote": "apostrophe",
    "`": "backtick",
    "backtick": "backtick",
    "grave": "backtick",
    "=": "equals",
    "equals": "equals",
    "[": "left bracket",
    "leftbracket": "left bracket",
    "left bracket": "left bracket",
    "]": "right bracket",
    "rightbracket": "right bracket",
    "right bracket": "right bracket",
}
LEGACY_KEY_NAMES = {
    "comma": ",",
    "minus": "-",
    "period": ".",
    "slash": "/",
    "backslash": "\\",
    "semicolon": ";",
    "apostrophe": "'",
    "backtick": "`",
    "equals": "=",
    "left bracket": "[",
    "right bracket": "]",
}
KEY_ALIASES = {
    "escape": "esc",
    "esc": "esc",
    "control": "ctrl",
    "ctrl": "ctrl",
    "strg": "ctrl",
    "steuerung": "ctrl",
    "leftctrl": "ctrl",
    "rightctrl": "ctrl",
    "ctrlleft": "ctrl",
    "ctrlright": "ctrl",
    "ctrll": "ctrl",
    "ctrlr": "ctrl",
    "shift": "shift",
    "leftshift": "shift",
    "rightshift": "shift",
    "shiftleft": "shift",
    "shiftright": "shift",
    "shiftl": "shift",
    "shiftr": "shift",
    "alt": "alt",
    "leftalt": "alt",
    "rightalt": "alt",
    "altleft": "alt",
    "altright": "alt",
    "altl": "alt",
    "altr": "alt",
    "altgr": "alt gr",
    "altgraph": "alt gr",
    "altgrkey": "alt gr",
    "cmd": "windows",
    "command": "windows",
    "meta": "windows",
    "super": "windows",
    "win": "windows",
    "windows": "windows",
    "cmdl": "windows",
    "cmdr": "windows",
    "space": "space",
    "spacebar": "space",
    "enter": "enter",
    "return": "enter",
    "backspace": "backspace",
    "tab": "tab",
    "delete": "delete",
    "del": "delete",
    "insert": "insert",
    "ins": "insert",
    "home": "home",
    "end": "end",
    "pageup": "page up",
    "pagedown": "page down",
    "page up": "page up",
    "page down": "page down",
    "capslock": "caps lock",
    "caps lock": "caps lock",
    "numlock": "num lock",
    "num lock": "num lock",
    "scrolllock": "scroll lock",
    "scroll lock": "scroll lock",
    "printscreen": "print screen",
    "print screen": "print screen",
    "prtsc": "print screen",
    "pause": "pause",
    "break": "pause",
    "menu": "menu",
    "contextmenu": "menu",
    "context menu": "menu",
    "arrowleft": "left",
    "arrowright": "right",
    "arrowup": "up",
    "arrowdown": "down",
    "left": "left",
    "right": "right",
    "up": "up",
    "down": "down",
}
NUMPAD_ALIASES = {
    "numpad0": "num 0",
    "numpad1": "num 1",
    "numpad2": "num 2",
    "numpad3": "num 3",
    "numpad4": "num 4",
    "numpad5": "num 5",
    "numpad6": "num 6",
    "numpad7": "num 7",
    "numpad8": "num 8",
    "numpad9": "num 9",
    "num0": "num 0",
    "num1": "num 1",
    "num2": "num 2",
    "num3": "num 3",
    "num4": "num 4",
    "num5": "num 5",
    "num6": "num 6",
    "num7": "num 7",
    "num8": "num 8",
    "num9": "num 9",
    "numpaddecimal": "num .",
    "numpaddivide": "num /",
    "numpadmultiply": "num *",
    "numpadsubtract": "num -",
    "numpadadd": "num +",
    "numpadenter": "num enter",
    "numpadequal": "num =",
    "numdecimal": "num .",
    "numdivide": "num /",
    "nummultiply": "num *",
    "numsubtract": "num -",
    "numadd": "num +",
    "numenter": "num enter",
    "numequal": "num =",
}
NUMPAD_VK_ALIASES = {
    96: "num 0",
    97: "num 1",
    98: "num 2",
    99: "num 3",
    100: "num 4",
    101: "num 5",
    102: "num 6",
    103: "num 7",
    104: "num 8",
    105: "num 9",
    106: "num *",
    107: "num +",
    109: "num -",
    110: "num .",
    111: "num /",
}
PYNPUT_OUTPUT_KEYS = {
    "esc": "esc",
    "ctrl": "ctrl",
    "shift": "shift",
    "alt": "alt",
    "alt gr": "alt_gr",
    "windows": "cmd",
    "space": "space",
    "enter": "enter",
    "backspace": "backspace",
    "tab": "tab",
    "delete": "delete",
    "insert": "insert",
    "home": "home",
    "end": "end",
    "page up": "page_up",
    "page down": "page_down",
    "caps lock": "caps_lock",
    "num lock": "num_lock",
    "scroll lock": "scroll_lock",
    "print screen": "print_screen",
    "pause": "pause",
    "menu": "menu",
    "left": "left",
    "right": "right",
    "up": "up",
    "down": "down",
    "num enter": "enter",
}
PYAUTOGUI_OUTPUT_KEYS = {
    "page up": "pageup",
    "page down": "pagedown",
    "caps lock": "capslock",
    "num lock": "numlock",
    "scroll lock": "scrolllock",
    "print screen": "printscreen",
    "left bracket": "[",
    "right bracket": "]",
    "num 0": "num0",
    "num 1": "num1",
    "num 2": "num2",
    "num 3": "num3",
    "num 4": "num4",
    "num 5": "num5",
    "num 6": "num6",
    "num 7": "num7",
    "num 8": "num8",
    "num 9": "num9",
    "num .": "decimal",
    "num /": "divide",
    "num *": "multiply",
    "num -": "subtract",
    "num +": "add",
    "num enter": "enter",
}


class FishingMode(str, Enum):
    TROPHY = "trophy"
    HYPE = "hype"
    FLAY = "flay"


@dataclass
class Hotkeys:
    stop: list[str] = field(default_factory=lambda: ["f1"])
    pause: list[str] = field(default_factory=lambda: ["enter"])
    timer_mode: list[str] = field(default_factory=lambda: ["f4"])
    fishing_mode: list[str] = field(default_factory=lambda: ["f6"])
    orb_mode: list[str] = field(default_factory=lambda: ["f7"])
    manual_override_keys: list[str] = field(default_factory=lambda: [str(number) for number in range(1, 10)])
    manual_override_mouse_buttons: list[str] = field(default_factory=lambda: ["mouse:right"])


@dataclass
class Config:
    config_version: int = CURRENT_CONFIG_VERSION

    # Screen area where the bite color appears: (left, top, width, height).
    region: tuple[int, int, int, int] = (1519, 724, 17, 50)
    target_rgb: tuple[int, int, int] = (252, 84, 84)
    tolerance: float = 20.0
    screen_backend: str = "auto"  # auto/mss = cross-platform, dxcam = Windows-only experiment
    input_backend: str = "auto"  # auto, pynput, legacy

    # Hotbar slots.
    rod_slot: list[str] = field(default_factory=lambda: ["4"])
    weapon_slot: list[str] = field(default_factory=lambda: ["3"])
    orb_slot: list[str] = field(default_factory=lambda: ["5"])

    # Timings.
    poll_interval: float = 0.05
    scan_interval: float = 0.12
    action_gap: float = FAST_ACTION_GAP
    post_cycle_gap: float = 0.50
    min_wait_time: float = 10.0
    key_debounce: float = 0.25
    manual_input_debounce: float = 0.20
    script_input_ignore: float = 0.80

    # Orb timing.
    orb_prepare_seconds: float = 50.0

    # Startup state.
    start_mode: str = "hype"
    timer_mode_enabled: bool = False
    orb_mode_enabled: bool = False
    hotkeys_enabled: bool = True

    hotkeys: Hotkeys = field(default_factory=Hotkeys)


CONFIG_DIR = Path(__file__).with_name("configs")
CONFIG_PATH = CONFIG_DIR / "fih.json"
LEGACY_CONFIG_PATH = Path(__file__).with_name("fih_config.json")
STOP_PATH = Path(__file__).with_name("fih_stop.flag")
CONTROL_PATH = Path(__file__).with_name("fih_control.json")


def merge_defaults(defaults, loaded):
    result = defaults.copy()
    for key, value in loaded.items():
        if key not in result:
            continue
        if isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_defaults(result[key], value)
        else:
            result[key] = value
    return result


def normalize_binding(value) -> str:
    binding = " ".join(str(value).strip().lower().replace("_", " ").split())
    if not binding or binding in {"none", "off"}:
        return ""
    if binding in MOUSE_BUTTON_ALIASES:
        return f"mouse:{MOUSE_BUTTON_ALIASES[binding]}"
    compact = binding.replace(" ", "")
    if binding in PUNCTUATION_KEY_ALIASES:
        return PUNCTUATION_KEY_ALIASES[binding]
    if compact in PUNCTUATION_KEY_ALIASES:
        return PUNCTUATION_KEY_ALIASES[compact]
    if compact in NUMPAD_ALIASES:
        return NUMPAD_ALIASES[compact]
    if compact in KEY_ALIASES:
        return KEY_ALIASES[compact]
    if binding in KEY_ALIASES:
        return KEY_ALIASES[binding]
    if compact.startswith("f") and compact[1:].isdigit():
        return compact
    return binding


def legacy_key_name(binding: str) -> str:
    return LEGACY_KEY_NAMES.get(normalize_binding(binding), normalize_binding(binding))


def pynput_output_key(binding: str):
    binding = normalize_binding(binding)
    if binding.startswith("f") and binding[1:].isdigit():
        key = getattr(pynput_keyboard.Key, binding, None)
        if key is not None:
            return key
    if binding.startswith("num ") and len(binding) == 5:
        return pynput_keyboard.KeyCode.from_char(binding[-1])
    key_name = PYNPUT_OUTPUT_KEYS.get(binding)
    if key_name:
        key = getattr(pynput_keyboard.Key, key_name, None)
        if key is not None:
            return key
    char = legacy_key_name(binding)
    if len(char) == 1:
        return pynput_keyboard.KeyCode.from_char(char)
    return binding


def pyautogui_key_name(binding: str) -> str:
    binding = normalize_binding(binding)
    if binding in LEGACY_KEY_NAMES:
        return LEGACY_KEY_NAMES[binding]
    return PYAUTOGUI_OUTPUT_KEYS.get(binding, binding)


def binding_list(value) -> list[str]:
    if value is None:
        return []

    if isinstance(value, list):
        raw_values = value
    else:
        raw_values = str(value).split(",")

    bindings = []
    for item in raw_values:
        binding = normalize_binding(item)
        if binding and binding not in bindings:
            bindings.append(binding)
    return bindings


def first_binding(value) -> str:
    bindings = binding_list(value)
    return bindings[0] if bindings else ""


def is_mouse_binding(binding: str) -> bool:
    return normalize_binding(binding).startswith("mouse:")


def mouse_button_from_binding(binding: str) -> str:
    return normalize_binding(binding).split(":", 1)[1]


def keyboard_bindings(bindings) -> list[str]:
    return [binding for binding in binding_list(bindings) if not is_mouse_binding(binding)]


def mouse_bindings(bindings) -> list[str]:
    return [binding for binding in binding_list(bindings) if is_mouse_binding(binding)]


def migrate_config(data: dict) -> dict:
    migrated = data.copy()
    config_version = int(migrated.get("config_version", 1))

    if config_version < 2:
        if float(migrated.get("action_gap", 0.12)) == 0.12:
            migrated["action_gap"] = FAST_ACTION_GAP
        migrated["config_version"] = CURRENT_CONFIG_VERSION

    if config_version < 3:
        hotkeys = migrated.get("hotkeys", {}).copy()
        hotkeys["pause"] = binding_list(hotkeys.get("pause", ["enter"]))
        hotkeys["manual_override_keys"] = keyboard_bindings(hotkeys.get("manual_override_keys", []))
        hotkeys["manual_override_mouse_buttons"] = mouse_bindings(
            hotkeys.get("manual_override_mouse_buttons", ["mouse:right"])
        )
        migrated["hotkeys"] = hotkeys
        migrated["config_version"] = CURRENT_CONFIG_VERSION

    if config_version < 4:
        hotkeys = migrated.get("hotkeys", {}).copy()
        for key in ("stop", "pause", "timer_mode", "fishing_mode", "orb_mode"):
            hotkeys[key] = binding_list(hotkeys.get(key, asdict(Hotkeys()).get(key, [])))
        migrated["hotkeys"] = hotkeys
        for key in ("rod_slot", "weapon_slot", "orb_slot"):
            migrated[key] = binding_list(migrated.get(key, asdict(Config()).get(key, [])))
        migrated["config_version"] = CURRENT_CONFIG_VERSION

    if config_version < 5:
        if float(migrated.get("action_gap", FAST_ACTION_GAP)) == 0.03:
            migrated["action_gap"] = FAST_ACTION_GAP
        migrated["config_version"] = CURRENT_CONFIG_VERSION

    return migrated


def config_from_dict(data: dict) -> Config:
    data = migrate_config(data)
    merged = merge_defaults(asdict(Config()), data)
    for key in ("rod_slot", "weapon_slot", "orb_slot"):
        merged[key] = binding_list(merged.get(key))
    hotkey_data = merged.pop("hotkeys")
    hotkey_data["stop"] = binding_list(hotkey_data.get("stop"))
    hotkey_data["pause"] = binding_list(hotkey_data.get("pause"))
    hotkey_data["timer_mode"] = binding_list(hotkey_data.get("timer_mode"))
    hotkey_data["fishing_mode"] = binding_list(hotkey_data.get("fishing_mode"))
    hotkey_data["orb_mode"] = binding_list(hotkey_data.get("orb_mode"))
    hotkey_data["manual_override_keys"] = keyboard_bindings(hotkey_data.get("manual_override_keys"))
    hotkey_data["manual_override_mouse_buttons"] = mouse_bindings(
        hotkey_data.get("manual_override_mouse_buttons")
    )
    hotkeys = Hotkeys(**hotkey_data)
    cfg = Config(**merged, hotkeys=hotkeys)
    cfg.region = tuple(cfg.region)
    cfg.target_rgb = tuple(cfg.target_rgb)
    return cfg


def save_config(cfg: Config, path: Path = CONFIG_PATH):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(cfg), indent=2) + "\n", encoding="utf-8")


def load_config(path: Path = CONFIG_PATH) -> Config:
    if not path.exists():
        if path == CONFIG_PATH and LEGACY_CONFIG_PATH.exists():
            try:
                data = json.loads(LEGACY_CONFIG_PATH.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise SystemExit(f"Config konnte nicht gelesen werden: {LEGACY_CONFIG_PATH}") from exc

            cfg = config_from_dict(data)
            save_config(cfg, path)
            print(f"Config migriert: {LEGACY_CONFIG_PATH.name} -> {path}")
            return cfg

        cfg = Config()
        save_config(cfg, path)
        print(f"Keine Config gefunden. Standardconfig erstellt: {path}")
        return cfg

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Config konnte nicht gelesen werden: {path}") from exc

    cfg = config_from_dict(data)
    save_config(cfg, path)
    print(f"Config geladen: {path}")
    return cfg


@dataclass
class Step:
    name: str
    action: Callable[[], None]
    delay_after: float = 0.0


class ScreenReader:
    def __init__(self, cfg: Config):
        left, top, width, height = cfg.region
        self.backend = self.choose_backend(cfg.screen_backend)

        if self.backend == "dxcam":
            self.region = (left, top, left + width, top + height)
            try:
                self.camera = dxcam.create(output_color="RGB")
                if self.camera is None:
                    raise OSError("dxcam.create returned None")
                self.sct = None
            except Exception as exc:
                print(f"dxcam konnte nicht gestartet werden ({exc}). Nutze mss.")
                self.backend = "mss"
                self.monitor = {"left": left, "top": top, "width": width, "height": height}
                self.sct = mss.mss()
                self.camera = None
        else:
            self.monitor = {"left": left, "top": top, "width": width, "height": height}
            self.sct = mss.mss()
            self.camera = None

        print(f"Screen-Backend: {self.backend}")

    @staticmethod
    def choose_backend(preferred: str) -> str:
        preferred = preferred.lower()
        is_windows = platform.system().lower() == "windows"

        if preferred == "dxcam":
            if not is_windows or dxcam is None:
                print("dxcam ist nicht verfuegbar. Nutze mss.")
                return "mss"
            return "dxcam"

        return "mss"

    def get_avg_rgb(self):
        if self.backend == "dxcam":
            frame = self.camera.grab(region=self.region)
            if frame is None:
                raise OSError("dxcam returned no frame")
            return np.asarray(frame).mean(axis=(0, 1))

        # mss returns BGRA bytes. The region is tiny, so averaging the array is cheap.
        frame = self.sct.grab(self.monitor)
        avg_bgra = np.asarray(frame).mean(axis=(0, 1))
        return avg_bgra[2], avg_bgra[1], avg_bgra[0]

    def close(self):
        if self.sct is not None:
            self.sct.close()
        if self.camera is not None:
            release = getattr(self.camera, "release", None)
            if callable(release):
                release()


class InputHooks:
    def __init__(self, helper: "FishingHelper"):
        self.helper = helper
        self.backend = self.choose_backend(helper.cfg.input_backend)
        self.hotkey_handles = []
        self.mouse_handles = []
        self.keyboard_listener = None
        self.mouse_listener = None

    @staticmethod
    def choose_backend(preferred: str) -> str:
        preferred = preferred.lower()
        is_windows = platform.system().lower() == "windows"
        legacy_available = legacy_keyboard is not None and legacy_mouse is not None
        pynput_available = pynput_keyboard is not None and pynput_mouse is not None

        if preferred == "pynput":
            if not pynput_available:
                print("pynput ist fuer dieses Python nicht verfuegbar. Versuche legacy Hotkey-Hooks.")
                return "legacy" if legacy_available else "none"
            return "pynput"

        if preferred == "legacy":
            if not legacy_available:
                print("legacy Hotkey-Hooks brauchen die Pakete keyboard und mouse. Versuche pynput.")
                return "pynput" if pynput_available else "none"
            return "legacy"

        if is_windows and legacy_available:
            return "legacy"

        if pynput_available:
            return "pynput"

        return "none"

    def start(self):
        if self.backend == "none":
            raise SystemExit(
                "Kein Hotkey-Backend verfuegbar.\n"
                "Installiere die Requirements mit genau diesem Python:\n"
                f"  {sys.executable} -m pip install -r requirements.txt"
            )

        if self.backend == "pynput":
            self.start_pynput()
        else:
            self.start_legacy()
        print(f"Hotkey-Backend: {self.backend}")

    def stop(self):
        if self.backend == "pynput":
            self.stop_pynput()
        elif self.backend == "legacy":
            self.stop_legacy()

    def start_pynput(self):
        self.keyboard_listener = pynput_keyboard.Listener(on_press=self.handle_pynput_key)
        self.mouse_listener = pynput_mouse.Listener(on_click=self.handle_pynput_click)
        self.keyboard_listener.start()
        self.mouse_listener.start()

    def stop_pynput(self):
        if self.keyboard_listener is not None:
            self.keyboard_listener.stop()
        if self.mouse_listener is not None:
            self.mouse_listener.stop()

    def handle_pynput_key(self, key):
        key_name = self.pynput_key_name(key)
        if key_name:
            self.helper.handle_binding_press(key_name)

    def handle_pynput_click(self, _x, _y, button, pressed):
        if pressed:
            button_name = getattr(button, "name", "")
            if button_name:
                self.helper.handle_binding_press(f"mouse:{button_name}")

    @staticmethod
    def pynput_key_name(key) -> str:
        vk = getattr(key, "vk", None)
        if vk in NUMPAD_VK_ALIASES:
            return NUMPAD_VK_ALIASES[vk]

        char = getattr(key, "char", None)
        if char:
            return normalize_binding(char)

        name = getattr(key, "name", None)
        return normalize_binding(name) if name else ""

    def start_legacy(self):
        hotkeys = self.helper.cfg.hotkeys
        for stop_binding in hotkeys.stop:
            self.bind_legacy(stop_binding, self.helper.request_stop)
        for pause_binding in hotkeys.pause:
            self.bind_legacy(pause_binding, self.helper.toggle_pause)
        for timer_binding in hotkeys.timer_mode:
            self.bind_legacy(timer_binding, self.helper.toggle_timer_mode)
        for fishing_binding in hotkeys.fishing_mode:
            self.bind_legacy(fishing_binding, self.helper.cycle_mode)
        for orb_binding in hotkeys.orb_mode:
            self.bind_legacy(orb_binding, self.helper.toggle_orb_mode)

        for binding in hotkeys.manual_override_keys + hotkeys.manual_override_mouse_buttons:
            self.bind_legacy(binding, lambda manual_binding=binding: self.helper.manual_override(manual_binding))

    def bind_legacy(self, binding: str, callback: Callable[[], None]):
        binding = normalize_binding(binding)
        if not binding:
            return

        if is_mouse_binding(binding):
            button = mouse_button_from_binding(binding)
            handle = legacy_mouse.on_button(callback, buttons=(button,), types=("down",))
            self.mouse_handles.append(handle)
            return

        handle = legacy_keyboard.on_press_key(legacy_key_name(binding), lambda _: callback())
        self.hotkey_handles.append(handle)

    def stop_legacy(self):
        for handle in self.hotkey_handles:
            legacy_keyboard.unhook(handle)
        self.hotkey_handles = []

        for handle in self.mouse_handles:
            legacy_mouse.unhook(handle)
        self.mouse_handles = []


class InputActions:
    def __init__(self, cfg: Config):
        self.backend = self.choose_backend(cfg.input_backend)
        self.keyboard_controller = None
        self.mouse_controller = None

        if self.backend == "pynput":
            self.keyboard_controller = pynput_keyboard.Controller()
            self.mouse_controller = pynput_mouse.Controller()

        print(f"Input-Ausgabe: {self.backend}")

    @staticmethod
    def choose_backend(preferred: str) -> str:
        preferred = preferred.lower()
        is_windows = platform.system().lower() == "windows"
        legacy_available = legacy_keyboard is not None and legacy_mouse is not None
        pynput_available = pynput_keyboard is not None and pynput_mouse is not None

        if preferred == "pynput":
            if pynput_available:
                return "pynput"
            if legacy_available:
                return "legacy"
            return "pyautogui"

        if preferred == "legacy":
            if legacy_available:
                return "legacy"
            if pynput_available:
                return "pynput"
            return "pyautogui"

        if is_windows and legacy_available:
            return "legacy"

        if pynput_available:
            return "pynput"

        return "pyautogui"

    def press_key(self, key: str):
        key = normalize_binding(key)
        if self.backend == "legacy":
            legacy_keyboard.press_and_release(legacy_key_name(key))
        elif self.backend == "pynput":
            output_key = pynput_output_key(key)
            self.keyboard_controller.press(output_key)
            self.keyboard_controller.release(output_key)
        else:
            pyautogui.press(pyautogui_key_name(key))

    def right_click(self):
        if self.backend == "legacy":
            legacy_mouse.click("right")
        elif self.backend == "pynput":
            self.mouse_controller.click(pynput_mouse.Button.right, 1)
        else:
            pyautogui.rightClick()

    def click_mouse_button(self, button: str):
        button = mouse_button_from_binding(button)
        if self.backend == "legacy":
            legacy_mouse.click(button)
        elif self.backend == "pynput":
            pynput_button = getattr(pynput_mouse.Button, button, None)
            if pynput_button is not None:
                self.mouse_controller.click(pynput_button, 1)
        else:
            pyautogui.click(button=button)

    def press_binding(self, binding: str):
        binding = normalize_binding(binding)
        if is_mouse_binding(binding):
            self.click_mouse_button(binding)
        else:
            self.press_key(binding)


class FishingHelper:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.lock = RLock()
        self.screen = ScreenReader(cfg)
        self.target_rgb = np.array(cfg.target_rgb, dtype=np.float32)
        self.tolerance_squared = cfg.tolerance * cfg.tolerance

        self.mode_order = [FishingMode.TROPHY, FishingMode.HYPE, FishingMode.FLAY]
        self.mode_index = self.mode_index_from_config()

        self.timer_mode_enabled = self.cfg.timer_mode_enabled
        self.orb_mode_enabled = self.cfg.orb_mode_enabled
        self.orb_pending = self.orb_mode_enabled

        self.paused = False
        self.stop_requested = False
        self.last_control_mtime = 0
        self.hotkeys_active = False
        self.last_hotkey_times = {}
        self.last_manual_input_time = 0.0
        self.ignore_manual_until = 0.0
        self.script_binding_events_to_ignore = {}

        self.last_cast_time = 0.0
        self.last_orb_time = time.monotonic()
        if self.orb_pending:
            self.last_orb_time -= self.cfg.orb_prepare_seconds
        self.next_scan_at = 0.0
        self.wait_for_color_reset = False

        # Current macro sequence. Only one step is executed per tick.
        self.steps: list[Step] = []
        self.step_index = 0
        self.next_step_at = 0.0

        self.input_actions = InputActions(cfg)
        self.input_hooks = InputHooks(self)

    @property
    def mode(self) -> FishingMode:
        return self.mode_order[self.mode_index]

    def mode_index_from_config(self) -> int:
        try:
            start_mode = FishingMode(self.cfg.start_mode.lower())
        except ValueError:
            print(f"Unbekannter start_mode in Config: {self.cfg.start_mode!r}. Nutze HYPE.")
            start_mode = FishingMode.HYPE
        return self.mode_order.index(start_mode)

    def current_step_name(self) -> str:
        if not self.steps:
            return "kein laufender Ablauf"
        return self.steps[self.step_index].name

    def print_controls(self):
        hotkeys = self.cfg.hotkeys
        stop_keys = ", ".join(hotkeys.stop)
        manual_keys = ", ".join(hotkeys.manual_override_keys)
        manual_buttons = ", ".join(hotkeys.manual_override_mouse_buttons)
        pause_keys = ", ".join(hotkeys.pause)
        timer_keys = ", ".join(hotkeys.timer_mode)
        fishing_keys = ", ".join(hotkeys.fishing_mode)
        orb_keys = ", ".join(hotkeys.orb_mode)

        print("Skript gestartet.")
        print(f"Python: {sys.executable}")
        print(
            "Pakete: "
            f"pynput={'OK' if pynput_keyboard is not None and pynput_mouse is not None else 'fehlt'} | "
            f"keyboard/mouse={'OK' if legacy_keyboard is not None and legacy_mouse is not None else 'fehlt'}"
        )
        print(
            f"Timing: action_gap={self.cfg.action_gap:.3f}s | "
            f"scan_interval={self.cfg.scan_interval:.3f}s | "
            f"script_input_ignore={self.cfg.script_input_ignore:.3f}s"
        )
        print(
            f"[{stop_keys or 'none'}] Beenden | [{pause_keys or 'none'}] Pause/Fortsetzen | "
            f"[{timer_keys or 'none'}] Timer | [{fishing_keys or 'none'}] Modus | [{orb_keys or 'none'}] Orb"
        )
        if not self.cfg.hotkeys_enabled:
            print("Script-Hotkeys sind deaktiviert. Steuerung laeuft ueber Sidechick.")
        print(f"Manueller Input ({manual_keys}; {manual_buttons}) verwirft den laufenden Ablauf.")
        self.print_mode_status()

    def mode_status_text(self) -> str:
        timer = "ON" if self.timer_mode_enabled else "OFF"
        orb = "ON" if self.orb_mode_enabled else "OFF"
        pending = "YES" if self.orb_pending else "NO"
        return f"Fishing={self.mode.value.upper()} | Timer={timer} | Orb={orb} | OrbPending={pending}"

    def print_mode_status(self):
        print(f"--> Modi: {self.mode_status_text()}")

    def hotkey_allowed(self, action_name: str, debounce: float | None = None) -> bool:
        now = time.monotonic()
        last_time = self.last_hotkey_times.get(action_name, 0.0)
        threshold = self.cfg.key_debounce if debounce is None else debounce
        if now - last_time < threshold:
            return False
        self.last_hotkey_times[action_name] = now
        return True

    def toggle_pause(self):
        with self.lock:
            if not self.hotkey_allowed("pause", PAUSE_KEY_DEBOUNCE):
                return

            self.set_pause(not self.paused)

    def set_pause(self, paused: bool):
        with self.lock:
            if self.paused == paused:
                return
            self.paused = paused
            if self.paused:
                print(f"--> PAUSE. Weiter geht es mit: {self.current_step_name()}")
            else:
                print("--> Weiter")

    def request_stop(self):
        with self.lock:
            self.stop_requested = True
            print("Beende...")

    def cycle_mode(self):
        with self.lock:
            if not self.hotkey_allowed("fishing_mode"):
                return
            mode = self.mode_order[(self.mode_index + 1) % len(self.mode_order)]
            self.set_fishing_mode(mode.value)

    def set_fishing_mode(self, mode: str):
        with self.lock:
            try:
                next_mode = FishingMode(str(mode).lower())
            except ValueError:
                print(f"Unbekannter Fishing-Modus vom Launcher: {mode!r}")
                return
            self.mode_index = self.mode_order.index(next_mode)
            print(f"--> Fishing-Modus: {self.mode.value.upper()}")
            self.print_mode_status()

    def toggle_timer_mode(self):
        with self.lock:
            if not self.hotkey_allowed("timer_mode"):
                return
            self.set_timer_mode(not self.timer_mode_enabled)

    def set_timer_mode(self, enabled: bool):
        with self.lock:
            self.timer_mode_enabled = bool(enabled)
            label = "TIMER (min. 10s)" if self.timer_mode_enabled else "NORMAL"
            print(f"--> Timer-Modus: {label}")
            self.print_mode_status()

    def toggle_orb_mode(self):
        with self.lock:
            if not self.hotkey_allowed("orb_mode"):
                return
            self.set_orb_mode(not self.orb_mode_enabled)

    def set_orb_mode(self, enabled: bool):
        with self.lock:
            self.orb_mode_enabled = bool(enabled)
            if self.orb_mode_enabled:
                self.orb_pending = True
                self.last_orb_time = time.monotonic() - self.cfg.orb_prepare_seconds
                label = "Orb (naechster Ablauf setzt Orb)"
            else:
                self.orb_pending = False
                label = "No Orb"
            print(f"--> Orb-Modus: {label}")
            self.print_mode_status()

    def set_orb_pending(self, pending: bool):
        with self.lock:
            self.orb_pending = bool(pending) and self.orb_mode_enabled
            state = "vorgemerkt" if self.orb_pending else "bereit"
            print(f"--> Orb-Placement: {state}")
            self.print_mode_status()

    def should_ignore_manual_input(self, now: float) -> bool:
        if now < self.ignore_manual_until:
            return True
        if now - self.last_manual_input_time < self.cfg.manual_input_debounce:
            return True
        self.last_manual_input_time = now
        return False

    def manual_override(self, source: str):
        with self.lock:
            now = time.monotonic()
            source = normalize_binding(source)
            if self.should_ignore_manual_input(now):
                return

            if self.steps:
                print(f"--> Manueller Eingriff ({source}): Ablauf verworfen.")

            self.steps = []
            self.step_index = 0
            self.next_step_at = 0.0
            self.next_scan_at = now + self.cfg.post_cycle_gap
            self.wait_for_color_reset = True

    def handle_binding_press(self, key: str):
        hotkeys = self.cfg.hotkeys
        key = normalize_binding(key)
        if not key:
            return

        with self.lock:
            ignored_count = self.script_binding_events_to_ignore.get(key, 0)
            if ignored_count > 0 and time.monotonic() < self.ignore_manual_until:
                if ignored_count == 1:
                    del self.script_binding_events_to_ignore[key]
                else:
                    self.script_binding_events_to_ignore[key] = ignored_count - 1
                return
            if time.monotonic() >= self.ignore_manual_until:
                self.script_binding_events_to_ignore.pop(key, None)

        if key in hotkeys.stop:
            self.request_stop()
        elif key in hotkeys.pause:
            self.toggle_pause()
        elif key in hotkeys.timer_mode:
            self.toggle_timer_mode()
        elif key in hotkeys.fishing_mode:
            self.cycle_mode()
        elif key in hotkeys.orb_mode:
            self.toggle_orb_mode()
        elif key in hotkeys.manual_override_keys or key in hotkeys.manual_override_mouse_buttons:
            self.manual_override(key)

    def register_hotkeys(self):
        if self.hotkeys_active or not self.cfg.hotkeys_enabled:
            return
        self.input_hooks.start()
        self.hotkeys_active = True

    def unregister_hotkeys(self):
        if not self.hotkeys_active:
            return
        self.input_hooks.stop()
        self.hotkeys_active = False

    def set_hotkeys_enabled(self, enabled: bool):
        enabled = bool(enabled)
        if self.cfg.hotkeys_enabled == enabled and self.hotkeys_active == enabled:
            return

        self.cfg.hotkeys_enabled = enabled
        if enabled:
            self.register_hotkeys()
            print("--> Script-Hotkeys: ON")
        else:
            self.unregister_hotkeys()
            print("--> Script-Hotkeys: OFF")

    def handle_control_file(self):
        if not CONTROL_PATH.exists():
            return

        try:
            stat = CONTROL_PATH.stat()
        except OSError:
            return

        if stat.st_mtime_ns == self.last_control_mtime:
            return
        self.last_control_mtime = stat.st_mtime_ns

        try:
            data = json.loads(CONTROL_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return

        command = data.get("command")
        if command == "stop":
            self.request_stop()
        elif command == "pause":
            self.set_pause(True)
        elif command == "resume":
            self.set_pause(False)
        elif command == "toggle_pause":
            self.set_pause(not self.paused)
        elif command == "set_fishing_mode":
            self.set_fishing_mode(data.get("mode", self.mode.value))
        elif command == "set_timer_mode":
            self.set_timer_mode(bool(data.get("enabled")))
        elif command == "set_orb_mode":
            self.set_orb_mode(bool(data.get("enabled")))
        elif command == "set_orb_pending":
            self.set_orb_pending(bool(data.get("pending")))
        elif command == "set_runtime_state":
            if "paused" in data:
                self.set_pause(bool(data.get("paused")))
            if "hotkeys_enabled" in data:
                self.set_hotkeys_enabled(bool(data.get("hotkeys_enabled")))
        elif command == "set_hotkeys_enabled":
            self.set_hotkeys_enabled(bool(data.get("enabled")))

    def is_bite_color(self) -> bool:
        avg_rgb = np.array(self.screen.get_avg_rgb(), dtype=np.float32)
        diff = avg_rgb - self.target_rgb
        return float(np.dot(diff, diff)) < self.tolerance_squared

    def should_start_cycle(self, now: float) -> bool:
        if not self.timer_mode_enabled:
            return True
        return (now - self.last_cast_time) >= self.cfg.min_wait_time

    def update_orb_state(self, now: float):
        if not self.orb_mode_enabled:
            self.orb_pending = False
            return

        if self.orb_pending:
            return

        if now - self.last_orb_time >= self.cfg.orb_prepare_seconds:
            self.orb_pending = True
            print("[ORB] Orb vorgemerkt: wird vor dem naechsten Auswerfen gesetzt")
            self.print_mode_status()

    def press_slot(self, slot):
        binding = first_binding(slot)
        if not binding:
            return
        self.run_script_input(lambda: self.input_actions.press_binding(binding), binding=binding)

    def right_click(self):
        self.run_script_input(self.input_actions.right_click, binding="mouse:right")

    def run_script_input(self, action: Callable[[], None], binding: str | None = None):
        with self.lock:
            if binding is not None:
                binding = normalize_binding(binding)
                self.script_binding_events_to_ignore[binding] = (
                    self.script_binding_events_to_ignore.get(binding, 0) + 1
                )

            self.ignore_manual_until = time.monotonic() + self.cfg.script_input_ignore
            action()
            self.ignore_manual_until = time.monotonic() + self.cfg.script_input_ignore

    def build_cycle(self) -> list[Step]:
        cycle_mode = self.mode
        gap = self.cfg.action_gap
        steps = [Step("Angel einholen", self.right_click, gap)]

        if cycle_mode in (FishingMode.HYPE, FishingMode.FLAY):
            steps.append(Step("Item auswaehlen", lambda: self.press_slot(self.cfg.weapon_slot), gap))

            uses = 2 if cycle_mode == FishingMode.HYPE else 1
            for number in range(1, uses + 1):
                steps.append(Step(f"Item benutzen {number}/{uses}", self.right_click, gap))

            steps.append(Step("Angel auswaehlen", lambda: self.press_slot(self.cfg.rod_slot), gap))

        if self.orb_mode_enabled and self.orb_pending:
            steps.extend(
                [
                    Step("Orb auswaehlen", lambda: self.press_slot(self.cfg.orb_slot), gap),
                    Step("Orb setzen", self.right_click, gap),
                    Step("Angel nach Orb auswaehlen", lambda: self.press_slot(self.cfg.rod_slot), gap),
                ]
            )

        steps.append(Step("Angel auswerfen", self.right_click, self.cfg.post_cycle_gap))
        return steps

    def start_cycle(self):
        with self.lock:
            self.steps = self.build_cycle()
            self.step_index = 0
            self.next_step_at = time.monotonic()
            self.wait_for_color_reset = False
            print("--> Ablauf gestartet")
            print("--> Ablauf: " + " -> ".join(step.name for step in self.steps))

    def finish_cycle(self):
        with self.lock:
            self.steps = []
            self.step_index = 0
            self.last_cast_time = time.monotonic()
            self.next_scan_at = self.last_cast_time + self.cfg.post_cycle_gap

    def run_one_step_if_ready(self, now: float):
        with self.lock:
            if not self.steps or self.paused or self.stop_requested:
                return

            if now < self.next_step_at:
                return

            step = self.steps[self.step_index]
            print(f"Schritt: {step.name}")
            step.action()

            if step.name == "Orb setzen":
                self.last_orb_time = time.monotonic()
                self.orb_pending = False
                self.print_mode_status()

            self.step_index += 1
            self.next_step_at = time.monotonic() + step.delay_after

            if self.step_index >= len(self.steps):
                self.finish_cycle()

    def scan_for_bite(self, now: float):
        self.next_scan_at = now + self.cfg.scan_interval
        self.update_orb_state(now)

        try:
            color_is_red = self.is_bite_color()
        except OSError:
            print("Warnung: Konnte Bildschirm nicht lesen. Warte kurz...")
            self.next_scan_at = time.monotonic() + 1.0
            return

        if self.wait_for_color_reset:
            if not color_is_red:
                self.wait_for_color_reset = False
                print("--> Wieder bereit: warte auf den naechsten Biss.")
            return

        if color_is_red and self.should_start_cycle(now):
            self.start_cycle()

    def tick(self):
        now = time.monotonic()

        if STOP_PATH.exists():
            self.request_stop()
            return

        self.handle_control_file()

        if self.paused:
            return

        if self.steps:
            self.run_one_step_if_ready(now)
            return

        if now < self.next_scan_at:
            return

        self.scan_for_bite(now)

    def run(self):
        self.print_controls()
        STOP_PATH.unlink(missing_ok=True)
        CONTROL_PATH.unlink(missing_ok=True)
        self.register_hotkeys()

        try:
            while not self.stop_requested:
                self.tick()
                time.sleep(self.cfg.poll_interval)
        finally:
            self.unregister_hotkeys()
            self.screen.close()
            STOP_PATH.unlink(missing_ok=True)
            CONTROL_PATH.unlink(missing_ok=True)


def main():
    FishingHelper(load_config()).run()


if __name__ == "__main__":
    main()
