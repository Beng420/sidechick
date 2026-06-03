import json
import shutil
import subprocess
import sys
import tempfile
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


class SidechickAPI:
    def __init__(self):
        self.runner = ProcessRunner()
        self.app_config = load_app_config()
        self.latest_release = None

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

        return {"ok": True, "message": f"Installed {self.latest_release['tag_name']} ({copied} files). Restart Sidechick."}

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
            "scan_interval": {"name": "set_scan_interval", "payload": {"seconds": float(value)}},
        }
        return commands.get(key)

    return None


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
