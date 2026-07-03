import json
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

from .config import (
    APP_DIR,
    APP_VERSION,
    CONFIG_DIR,
    SCRIPT_DEFINITIONS,
    UPDATE_REPO,
    load_app_config,
    load_script_config,
    public_script,
    save_app_config,
    save_script_config,
)
from .process_runner import ProcessRunner


RELEASES_API_URL = f"https://api.github.com/repos/{UPDATE_REPO}/releases?per_page=20"
REQUIREMENTS_PATH = APP_DIR / "requirements.txt"
PENDING_CHANGELOG_PATH = CONFIG_DIR / "pending_changelog.json"
UPDATE_KEEP_PARTS = {".git", "__pycache__", "configs", "runtime"}
UPDATE_KEEP_FILES = {
    "fih_config.json",
    "sidechick_config.json",
    "fih_stop.flag",
    "superpairs_stop.flag",
    "fih_control.json",
    "superpairs_control.json",
}
UPDATE_ALLOWED_SUFFIXES = {".py", ".pyw", ".md", ".txt", ".html", ".css", ".js", ".png", ".ico"}


def enable_dpi_awareness():
    if not sys.platform.startswith("win"):
        return
    try:
        import ctypes

        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


class SidechickAPI:
    def __init__(self):
        self.runner = ProcessRunner()
        self.app_config = load_app_config()
        self.latest_release = None
        self.coordinate_search_cancel = threading.Event()

    def get_state(self):
        scripts = [public_script(script_id) for script_id in SCRIPT_DEFINITIONS]
        selected = self.app_config.get("selected_script", "fih")
        if selected not in SCRIPT_DEFINITIONS:
            selected = "fih"
        process_state = self.runner.poll(selected)

        return {
            "app_version": APP_VERSION,
            "app_config": self.app_config,
            "scripts": scripts,
            "selected_script": selected,
            "selected_config": load_script_config(selected),
            "process": process_state,
            "update": self.update_summary(),
            "pending_changelog": read_pending_changelog(),
        }

    def select_script(self, script_id):
        if script_id not in SCRIPT_DEFINITIONS:
            return {"ok": False, "message": "Unknown script."}
        self.app_config["selected_script"] = script_id
        self.app_config = save_app_config(self.app_config)
        self.focus_script_hotkeys(script_id)
        return {"ok": True, "state": self.get_state()}

    def save_app_config(self, config):
        self.app_config = save_app_config(config)
        return {"ok": True, "app_config": self.app_config}

    def get_script_config(self, script_id):
        if script_id not in SCRIPT_DEFINITIONS:
            return {"ok": False, "message": "Unknown script."}
        return {"ok": True, "config": load_script_config(script_id)}

    def save_script_config(self, script_id, config):
        if script_id not in SCRIPT_DEFINITIONS:
            return {"ok": False, "message": "Unknown script."}
        return {"ok": True, "config": save_script_config(script_id, config)}

    def start_script(self, script_id):
        if script_id not in SCRIPT_DEFINITIONS:
            return {"ok": False, "message": "Unknown script."}
        self.app_config["selected_script"] = script_id
        self.app_config = save_app_config(self.app_config)
        self.focus_script_hotkeys(script_id)
        self.pause_other_scripts(script_id)
        load_script_config(script_id)
        return self.runner.start(script_id)

    def stop_script(self, script_id=None):
        script_id = self.resolve_script_id(script_id)
        return self.runner.stop(script_id)

    def pause_script(self, script_id=None, paused=None):
        script_id = self.resolve_script_id(script_id)
        return self.runner.pause(script_id, paused)

    def set_runtime_option(self, script_id, key, value):
        if script_id not in SCRIPT_DEFINITIONS:
            return {"ok": False, "message": "Unknown script."}

        config = load_script_config(script_id)
        set_by_path(config, key, value)
        config = save_script_config(script_id, config)

        command = runtime_command_for(script_id, key, value)
        if command and self.runner.is_running(script_id):
            self.runner.send_command(script_id, command["name"], **command.get("payload", {}))

        return {"ok": True, "config": config, "process": self.runner.poll(script_id)}

    def find_fih_region(self, config):
        config = save_script_config("fih", config)
        self.coordinate_search_cancel.clear()

        try:
            found, marked, cancelled = find_target_with_click_updates(
                config,
                radius=30,
                timeout=20.0,
                cancel_event=self.coordinate_search_cancel,
            )
        except Exception as exc:
            return {"ok": False, "message": str(exc), "config": config}

        if cancelled:
            return {"ok": False, "message": "Coordinate search cancelled.", "config": config}

        if not found:
            marked_text = f"marked position ({marked[0]}, {marked[1]})" if marked else "a clicked position"
            return {
                "ok": False,
                "message": f"No target color found within 30px of {marked_text} in 20 seconds.",
                "config": config,
            }

        left, top = found
        config["region"][0] = int(left)
        config["region"][1] = int(top)
        config = save_script_config("fih", config)
        return {
            "ok": True,
            "message": f"Region top-left saved at ({left}, {top}).",
            "config": config,
        }

    def cancel_fih_region_search(self):
        self.coordinate_search_cancel.set()
        return {"ok": True, "message": "Coordinate search cancellation requested."}

    def drain_logs(self, script_id=None):
        script_id = self.resolve_script_id(script_id)
        return {"logs": self.runner.drain_logs(script_id), "process": self.runner.poll(script_id)}

    def install_requirements(self):
        if not REQUIREMENTS_PATH.exists():
            return {"ok": False, "message": "requirements.txt was not found."}

        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(REQUIREMENTS_PATH)],
            cwd=str(APP_DIR),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        return {
            "ok": result.returncode == 0,
            "message": "Requirements installed." if result.returncode == 0 else "Requirements install failed.",
            "output": result.stdout,
        }

    def check_updates(self):
        try:
            release = fetch_latest_release()
        except Exception as exc:
            return {"ok": False, "message": str(exc)}

        self.latest_release = release
        return {"ok": True, "update": self.update_summary()}

    def install_update(self):
        if self.runner.is_running():
            return {"ok": False, "message": "Stop the running script before updating."}
        if not self.latest_release:
            checked = self.check_updates()
            if not checked.get("ok"):
                return checked
        if not version_is_newer(self.latest_release["tag_name"], APP_VERSION):
            return {"ok": False, "message": "No newer release available."}

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp_path = Path(tmpdir)
                zip_path = tmp_path / "release.zip"
                download_release_zip(self.latest_release, zip_path)
                extract_dir = tmp_path / "release"
                extract_dir.mkdir()
                with zipfile.ZipFile(zip_path, "r") as archive:
                    archive.extractall(extract_dir)
                source_dir = find_release_root(extract_dir)
                copied = copy_update_files(source_dir, APP_DIR)
        except Exception as exc:
            return {"ok": False, "message": str(exc)}

        write_pending_changelog(self.latest_release, copied)
        return {"ok": True, "message": f"Installed {self.latest_release['tag_name']} ({copied} files). Restart Sidechick."}

    def dismiss_update_changelog(self):
        try:
            PENDING_CHANGELOG_PATH.unlink(missing_ok=True)
        except OSError as exc:
            return {"ok": False, "message": str(exc)}
        return {"ok": True}

    def update_summary(self):
        if not self.latest_release:
            return {"checked": False, "message": "Updates not checked.", "available": False}

        latest_version = self.latest_release["tag_name"]
        release_kind = "pre-release" if self.latest_release.get("prerelease") else "release"
        if version_is_newer(latest_version, APP_VERSION):
            message = f"Found {latest_version} ({release_kind}). Update available."
            available = True
        elif same_version(latest_version, APP_VERSION):
            message = f"Found {latest_version} ({release_kind}). You are up to date."
            available = False
        else:
            message = f"Found {latest_version} ({release_kind}). Local version {APP_VERSION} is newer."
            available = False
        return {"checked": True, "message": message, "available": available, "version": latest_version}

    def shutdown(self):
        self.runner.close()
        return {"ok": True}

    def resolve_script_id(self, script_id):
        if script_id in SCRIPT_DEFINITIONS:
            return script_id
        selected = self.app_config.get("selected_script", "fih")
        return selected if selected in SCRIPT_DEFINITIONS else "fih"

    def pause_other_scripts(self, selected_script_id):
        for script_id in SCRIPT_DEFINITIONS:
            if script_id == selected_script_id:
                continue
            if self.runner.is_running(script_id):
                self.runner.set_runtime_state(script_id, paused=True, hotkeys_enabled=False)

    def focus_script_hotkeys(self, selected_script_id):
        for script_id in SCRIPT_DEFINITIONS:
            enabled = script_id == selected_script_id
            config = load_script_config(script_id)
            if "hotkeys_enabled" in config and config["hotkeys_enabled"] != enabled:
                config["hotkeys_enabled"] = enabled
                save_script_config(script_id, config)
            if self.runner.is_running(script_id):
                self.runner.set_runtime_state(script_id, hotkeys_enabled=enabled)


def set_by_path(data, path, value):
    parts = path.split(".")
    current = data
    for part in parts[:-1]:
        current = current[part]
    current[parts[-1]] = value


def find_target_with_click_updates(config, radius, timeout, cancel_event=None):
    enable_dpi_awareness()

    try:
        from pynput import keyboard as pynput_keyboard
        from pynput import mouse as pynput_mouse
    except ImportError as exc:
        raise RuntimeError("pynput is required for coordinate search. Install requirements first.") from exc

    try:
        import mss
    except ImportError as exc:
        raise RuntimeError("mss is required for coordinate search. Install requirements first.") from exc

    if cancel_event is None:
        cancel_event = threading.Event()

    lock = threading.Lock()
    latest = {"x": None, "y": None, "deadline": None}
    first_click_deadline = time.monotonic() + timeout
    marker = CoordinateMarkerProcess(radius=radius)

    def on_click(x, y, button, pressed):
        if pressed and button == pynput_mouse.Button.left:
            with lock:
                latest["x"] = int(x)
                latest["y"] = int(y)
                latest["deadline"] = time.monotonic() + timeout
            marker.show(int(x), int(y))
        return None

    def on_press(key):
        if key == pynput_keyboard.Key.esc:
            cancel_event.set()
            return False
        return None

    mouse_listener = pynput_mouse.Listener(on_click=on_click)
    keyboard_listener = pynput_keyboard.Listener(on_press=on_press)
    marker.start()
    mouse_listener.start()
    keyboard_listener.start()
    try:
        with mss.mss() as sct:
            while True:
                if cancel_event.is_set():
                    with lock:
                        x = latest["x"]
                        y = latest["y"]
                    marked = (x, y) if x is not None and y is not None else None
                    return None, marked, True

                with lock:
                    x = latest["x"]
                    y = latest["y"]
                    deadline = latest["deadline"]

                now = time.monotonic()
                if x is None or y is None:
                    if now >= first_click_deadline:
                        raise RuntimeError("Coordinate search timed out while waiting for a left click.")
                    time.sleep(0.05)
                    continue

                if now >= deadline:
                    return None, (x, y), False

                found = scan_once_for_target_color(sct, config, x, y, radius)
                if found:
                    return found, (x, y), False

                time.sleep(0.05)
    finally:
        mouse_listener.stop()
        keyboard_listener.stop()
        marker.close()


class CoordinateMarkerProcess:
    def __init__(self, radius):
        self.radius = int(radius)
        self.process = None
        self.monitor = None

    def start(self):
        try:
            import mss
        except ImportError:
            return

        with mss.mss() as sct:
            virtual = sct.monitors[0]
            self.monitor = {
                "left": int(virtual["left"]),
                "top": int(virtual["top"]),
                "width": int(virtual["width"]),
                "height": int(virtual["height"]),
            }

        script_path = APP_DIR / "backend" / "coordinate_marker.py"
        startupinfo = None
        creationflags = 0
        if sys.platform.startswith("win"):
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

        try:
            self.process = subprocess.Popen(
                [sys.executable, str(script_path)],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True,
                cwd=str(APP_DIR),
                startupinfo=startupinfo,
                creationflags=creationflags,
            )
        except OSError:
            self.process = None

    def show(self, x, y):
        self.send({"command": "show", "x": int(x), "y": int(y), "radius": self.radius, "monitor": self.monitor})

    def close(self):
        self.send({"command": "close"})
        if self.process is None:
            return
        try:
            self.process.wait(timeout=1.0)
        except subprocess.TimeoutExpired:
            self.process.terminate()
        self.process = None

    def send(self, payload):
        if self.process is None or self.process.stdin is None:
            return
        if self.process.poll() is not None:
            return
        try:
            self.process.stdin.write(json.dumps(payload) + "\n")
            self.process.stdin.flush()
        except OSError:
            pass


def scan_once_for_target_color(sct, config, click_x, click_y, radius):
    target = tuple(int(value) for value in config.get("target_rgb", [252, 84, 84]))
    tolerance = float(config.get("tolerance", 20.0))
    tolerance_squared = tolerance * tolerance

    virtual = sct.monitors[0]
    virtual_left = int(virtual["left"])
    virtual_top = int(virtual["top"])
    virtual_right = virtual_left + int(virtual["width"])
    virtual_bottom = virtual_top + int(virtual["height"])

    left = max(virtual_left, int(click_x) - radius)
    top = max(virtual_top, int(click_y) - radius)
    right = min(virtual_right, int(click_x) + radius + 1)
    bottom = min(virtual_bottom, int(click_y) + radius + 1)
    if right <= left or bottom <= top:
        raise RuntimeError("Clicked point is outside the captured screen area.")

    monitor = {"left": left, "top": top, "width": right - left, "height": bottom - top}
    frame = sct.grab(monitor)
    raw = frame.raw
    stride = frame.width * 4
    min_x = None
    min_y = None

    for y in range(frame.height):
        row = y * stride
        for x in range(frame.width):
            index = row + x * 4
            b = raw[index]
            g = raw[index + 1]
            r = raw[index + 2]
            diff = (
                (r - target[0]) * (r - target[0])
                + (g - target[1]) * (g - target[1])
                + (b - target[2]) * (b - target[2])
            )
            if diff <= tolerance_squared:
                if min_x is None or x < min_x:
                    min_x = x
                if min_y is None or y < min_y:
                    min_y = y

    if min_x is not None and min_y is not None:
        return left + min_x, top + min_y

    return None


def runtime_command_for(script_id, key, value):
    if script_id == "fih":
        commands = {
            "start_mode": {"name": "set_fishing_mode", "payload": {"mode": value}},
            "timer_mode_enabled": {"name": "set_timer_mode", "payload": {"enabled": bool(value)}},
            "orb_mode_enabled": {"name": "set_orb_mode", "payload": {"enabled": bool(value)}},
        }
        return commands.get(key)

    if script_id == "superpairs":
        commands = {
            "click_cooldown": {"name": "set_click_cooldown", "payload": {"seconds": float(value)}},
            "pre_click_delay": {"name": "set_pre_click_delay", "payload": {"seconds": float(value)}},
            "scan_interval": {"name": "set_scan_interval", "payload": {"seconds": float(value)}},
        }
        return commands.get(key)

    return None


def read_pending_changelog():
    if not PENDING_CHANGELOG_PATH.exists():
        return None
    try:
        changelog = json.loads(PENDING_CHANGELOG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    version = str(changelog.get("version") or "")
    if version and version_is_newer(version, APP_VERSION):
        return None
    return changelog


def write_pending_changelog(release, copied_files):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    body = str(release.get("body") or "").strip()
    if not body:
        body = "No changelog was provided for this release."
    payload = {
        "version": release.get("tag_name", "unknown"),
        "name": release.get("name") or release.get("tag_name", "Update"),
        "body": body,
        "url": release.get("html_url", ""),
        "copied_files": copied_files,
    }
    PENDING_CHANGELOG_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def fetch_latest_release():
    request = urllib.request.Request(
        RELEASES_API_URL,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"sidechick/{APP_VERSION}",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            releases = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise RuntimeError("No public release found yet, or repo is not reachable") from exc
        raise RuntimeError(f"GitHub returned HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not reach GitHub: {exc.reason}") from exc

    for release in releases:
        if not release.get("draft"):
            return release
    raise RuntimeError("No published release found yet")


def version_tuple(version: str):
    cleaned = version.strip().lower().lstrip("v")
    parts = []
    current = ""
    for char in cleaned:
        if char.isdigit():
            current += char
        elif current:
            parts.append(int(current))
            current = ""
    if current:
        parts.append(int(current))
    return tuple(parts[:3])


def version_is_newer(latest: str, current: str) -> bool:
    latest_parts = version_tuple(latest)
    current_parts = version_tuple(current)
    max_length = max(len(latest_parts), len(current_parts), 3)
    latest_parts = latest_parts + (0,) * (max_length - len(latest_parts))
    current_parts = current_parts + (0,) * (max_length - len(current_parts))
    return latest_parts > current_parts


def same_version(left: str, right: str) -> bool:
    left_parts = version_tuple(left)
    right_parts = version_tuple(right)
    max_length = max(len(left_parts), len(right_parts), 3)
    left_parts = left_parts + (0,) * (max_length - len(left_parts))
    right_parts = right_parts + (0,) * (max_length - len(right_parts))
    return left_parts == right_parts


def release_download_url(release):
    zip_assets = [
        asset
        for asset in release.get("assets", [])
        if asset.get("name", "").lower().endswith(".zip")
    ]
    if zip_assets:
        return zip_assets[0]["browser_download_url"]
    return release["zipball_url"]


def download_release_zip(release, destination: Path):
    request = urllib.request.Request(
        release_download_url(release),
        headers={"User-Agent": f"sidechick/{APP_VERSION}"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        destination.write_bytes(response.read())


def find_release_root(extract_dir: Path) -> Path:
    children = [path for path in extract_dir.iterdir() if path.is_dir()]
    if len(children) == 1:
        return children[0]
    return extract_dir


def should_copy_update_file(path: Path) -> bool:
    if path.name in UPDATE_KEEP_FILES:
        return False
    if any(part in UPDATE_KEEP_PARTS for part in path.parts):
        return False
    return path.suffix.lower() in UPDATE_ALLOWED_SUFFIXES


def copy_update_files(source_dir: Path, target_dir: Path):
    copied = 0
    for source in source_dir.rglob("*"):
        if not source.is_file():
            continue
        relative = source.relative_to(source_dir)
        if not should_copy_update_file(relative):
            continue
        target = target_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied += 1
    if copied == 0:
        raise RuntimeError("No update files were found in the release ZIP.")
    return copied
