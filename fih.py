import json
import platform
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


class FishingMode(str, Enum):
    TROPHY = "trophy"
    HYPE = "hype"
    FLAY = "flay"


@dataclass
class Hotkeys:
    stop: str = "f1"
    pause: str = "enter"
    timer_mode: str = "f4"
    fishing_mode: str = "f6"
    orb_mode: str = "f7"
    manual_override_keys: list[str] = field(default_factory=lambda: [str(number) for number in range(1, 10)])


@dataclass
class Config:
    # Screen area where the bite color appears: (left, top, width, height).
    region: tuple[int, int, int, int] = (1519, 724, 17, 50)
    target_rgb: tuple[int, int, int] = (252, 84, 84)
    tolerance: float = 20.0
    screen_backend: str = "auto"  # auto/mss = cross-platform, dxcam = Windows-only experiment
    input_backend: str = "auto"  # auto, pynput, legacy

    # Hotbar slots.
    rod_slot: str = "4"
    weapon_slot: str = "3"
    orb_slot: str = "5"

    # Timings.
    poll_interval: float = 0.05
    scan_interval: float = 0.12
    action_gap: float = 0.12
    post_cycle_gap: float = 0.50
    min_wait_time: float = 10.0
    key_debounce: float = 0.25
    manual_input_debounce: float = 0.20
    script_input_ignore: float = 0.80

    # HYPE orb timing.
    orb_prepare_seconds: float = 50.0

    # Startup state.
    start_mode: str = "hype"
    timer_mode_enabled: bool = False
    orb_mode_enabled: bool = False

    hotkeys: Hotkeys = field(default_factory=Hotkeys)


CONFIG_PATH = Path(__file__).with_name("fih_config.json")
STOP_PATH = Path(__file__).with_name("fih_stop.flag")


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


def config_from_dict(data: dict) -> Config:
    merged = merge_defaults(asdict(Config()), data)
    hotkeys = Hotkeys(**merged.pop("hotkeys"))
    cfg = Config(**merged, hotkeys=hotkeys)
    cfg.region = tuple(cfg.region)
    cfg.target_rgb = tuple(cfg.target_rgb)
    cfg.hotkeys.manual_override_keys = [str(key) for key in cfg.hotkeys.manual_override_keys]
    return cfg


def save_config(cfg: Config, path: Path = CONFIG_PATH):
    path.write_text(json.dumps(asdict(cfg), indent=2) + "\n", encoding="utf-8")


def load_config(path: Path = CONFIG_PATH) -> Config:
    if not path.exists():
        cfg = Config()
        save_config(cfg, path)
        print(f"Keine Config gefunden. Standardconfig erstellt: {path.name}")
        return cfg

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Config konnte nicht gelesen werden: {path}") from exc

    cfg = config_from_dict(data)
    save_config(cfg, path)
    print(f"Config geladen: {path.name}")
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

        if preferred == "pynput":
            if pynput_keyboard is None or pynput_mouse is None:
                print("pynput ist nicht installiert. Nutze legacy Input-Hooks.")
                return "legacy"
            return "pynput"

        if preferred == "legacy":
            return "legacy"

        if is_windows and legacy_keyboard is not None and legacy_mouse is not None:
            return "legacy"

        if pynput_keyboard is not None and pynput_mouse is not None:
            return "pynput"

        return "legacy"

    def start(self):
        if self.backend == "pynput":
            self.start_pynput()
        else:
            self.start_legacy()
        print(f"Input-Backend: {self.backend}")

    def stop(self):
        if self.backend == "pynput":
            self.stop_pynput()
        else:
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
            self.helper.handle_key_press(key_name)

    def handle_pynput_click(self, _x, _y, button, pressed):
        if pressed and button == pynput_mouse.Button.right:
            self.helper.manual_override("Rechtsklick")

    @staticmethod
    def pynput_key_name(key) -> str:
        char = getattr(key, "char", None)
        if char:
            return char.lower()

        name = getattr(key, "name", None)
        return name.lower() if name else ""

    def start_legacy(self):
        if legacy_keyboard is None or legacy_mouse is None:
            raise SystemExit("Kein Input-Backend verfuegbar. Installiere am besten: pip install pynput")

        hotkeys = self.helper.cfg.hotkeys
        self.hotkey_handles = [
            legacy_keyboard.on_press_key(hotkeys.stop, lambda _: self.helper.request_stop()),
            legacy_keyboard.on_press_key(hotkeys.pause, lambda _: self.helper.toggle_pause()),
            legacy_keyboard.on_press_key(hotkeys.timer_mode, lambda _: self.helper.toggle_timer_mode()),
            legacy_keyboard.on_press_key(hotkeys.fishing_mode, lambda _: self.helper.cycle_mode()),
            legacy_keyboard.on_press_key(hotkeys.orb_mode, lambda _: self.helper.toggle_orb_mode()),
        ]
        self.hotkey_handles.extend(
            legacy_keyboard.on_press_key(key, lambda _, manual_key=key: self.helper.manual_override(manual_key))
            for key in hotkeys.manual_override_keys
        )
        self.mouse_handles = [
            legacy_mouse.on_right_click(lambda: self.helper.manual_override("Rechtsklick")),
        ]

    def stop_legacy(self):
        for handle in self.hotkey_handles:
            legacy_keyboard.unhook(handle)
        self.hotkey_handles = []

        for handle in self.mouse_handles:
            legacy_mouse.unhook(handle)
        self.mouse_handles = []


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
        self.orb_pending = False

        self.paused = False
        self.stop_requested = False
        self.last_hotkey_time = 0.0
        self.last_manual_input_time = 0.0
        self.ignore_manual_until = 0.0
        self.script_key_events_to_ignore = {}
        self.script_right_clicks_to_ignore = 0

        self.last_cast_time = 0.0
        self.last_orb_time = time.monotonic()
        self.next_scan_at = 0.0
        self.wait_for_color_reset = False

        # Current macro sequence. Only one step is executed per tick.
        self.steps: list[Step] = []
        self.step_index = 0
        self.next_step_at = 0.0

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
        manual_keys = ", ".join(hotkeys.manual_override_keys)

        print("Skript gestartet.")
        print(
            f"[{hotkeys.stop}] Beenden | [{hotkeys.pause}] Pause/Fortsetzen | "
            f"[{hotkeys.timer_mode}] Timer | [{hotkeys.fishing_mode}] Modus | [{hotkeys.orb_mode}] Orb"
        )
        print(f"Manueller Rechtsklick oder Taste {manual_keys} verwirft den laufenden Ablauf.")
        print(f"Aktiver Fishing-Modus: {self.mode.value.upper()}")

    def hotkey_allowed(self) -> bool:
        now = time.monotonic()
        if now - self.last_hotkey_time < self.cfg.key_debounce:
            return False
        self.last_hotkey_time = now
        return True

    def toggle_pause(self):
        with self.lock:
            if not self.hotkey_allowed():
                return

            self.paused = not self.paused
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
            if not self.hotkey_allowed():
                return
            self.mode_index = (self.mode_index + 1) % len(self.mode_order)
            print(f"--> Fishing-Modus: {self.mode.value.upper()}")

    def toggle_timer_mode(self):
        with self.lock:
            if not self.hotkey_allowed():
                return
            self.timer_mode_enabled = not self.timer_mode_enabled
            label = "TIMER (min. 10s)" if self.timer_mode_enabled else "NORMAL"
            print(f"--> Timer-Modus: {label}")

    def toggle_orb_mode(self):
        with self.lock:
            if not self.hotkey_allowed():
                return
            self.orb_mode_enabled = not self.orb_mode_enabled
            label = "Orb" if self.orb_mode_enabled else "No Orb"
            print(f"--> Orb-Modus: {label}")

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
            if source == "Rechtsklick" and self.script_right_clicks_to_ignore > 0 and now < self.ignore_manual_until:
                self.script_right_clicks_to_ignore -= 1
                return
            if now >= self.ignore_manual_until:
                self.script_right_clicks_to_ignore = 0

            if self.should_ignore_manual_input(now):
                return

            if self.steps:
                print(f"--> Manueller Eingriff ({source}): Ablauf verworfen.")

            self.steps = []
            self.step_index = 0
            self.next_step_at = 0.0
            self.next_scan_at = now + self.cfg.post_cycle_gap
            self.wait_for_color_reset = True

    def handle_key_press(self, key: str):
        hotkeys = self.cfg.hotkeys
        key = key.lower()

        with self.lock:
            ignored_count = self.script_key_events_to_ignore.get(key, 0)
            if ignored_count > 0 and time.monotonic() < self.ignore_manual_until:
                if ignored_count == 1:
                    del self.script_key_events_to_ignore[key]
                else:
                    self.script_key_events_to_ignore[key] = ignored_count - 1
                return
            if time.monotonic() >= self.ignore_manual_until:
                self.script_key_events_to_ignore.pop(key, None)

        if key == hotkeys.stop.lower():
            self.request_stop()
        elif key == hotkeys.pause.lower():
            self.toggle_pause()
        elif key == hotkeys.timer_mode.lower():
            self.toggle_timer_mode()
        elif key == hotkeys.fishing_mode.lower():
            self.cycle_mode()
        elif key == hotkeys.orb_mode.lower():
            self.toggle_orb_mode()
        elif key in [manual_key.lower() for manual_key in hotkeys.manual_override_keys]:
            self.manual_override(key)

    def register_hotkeys(self):
        self.input_hooks.start()

    def unregister_hotkeys(self):
        self.input_hooks.stop()

    def is_bite_color(self) -> bool:
        avg_rgb = np.array(self.screen.get_avg_rgb(), dtype=np.float32)
        diff = avg_rgb - self.target_rgb
        return float(np.dot(diff, diff)) < self.tolerance_squared

    def should_start_cycle(self, now: float) -> bool:
        if not self.timer_mode_enabled:
            return True
        return (now - self.last_cast_time) >= self.cfg.min_wait_time

    def update_orb_state(self, now: float):
        if self.mode != FishingMode.HYPE:
            self.orb_pending = False
            return

        if self.orb_pending:
            return

        if now - self.last_orb_time >= self.cfg.orb_prepare_seconds:
            self.orb_pending = True
            print("[HYPE] Orb vorgemerkt: wird vor dem naechsten Auswerfen gesetzt")

    def press_slot(self, slot: str):
        self.run_script_input(lambda: pyautogui.press(slot), key=slot)

    def right_click(self):
        self.run_script_input(pyautogui.rightClick, right_click=True)

    def run_script_input(self, action: Callable[[], None], key: str | None = None, right_click: bool = False):
        with self.lock:
            if key is not None:
                key = key.lower()
                self.script_key_events_to_ignore[key] = self.script_key_events_to_ignore.get(key, 0) + 1

            if right_click:
                self.script_right_clicks_to_ignore += 1

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
        self.register_hotkeys()

        try:
            while not self.stop_requested:
                self.tick()
                time.sleep(self.cfg.poll_interval)
        finally:
            self.unregister_hotkeys()
            self.screen.close()
            STOP_PATH.unlink(missing_ok=True)


def main():
    FishingHelper(load_config()).run()


if __name__ == "__main__":
    main()
