import json
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import tkinter as tk
import threading
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from tkinter import BooleanVar, DoubleVar, IntVar, StringVar, Tk, messagebox
from tkinter import ttk


APP_DIR = Path(__file__).resolve().parent
APP_VERSION = "v1.4.1"
UPDATE_REPO = "Beng420/sidechick"
SCRIPT_PATH = APP_DIR / "fih.py"
CONFIG_PATH = APP_DIR / "fih_config.json"
STOP_PATH = APP_DIR / "fih_stop.flag"
RELEASES_API_URL = f"https://api.github.com/repos/{UPDATE_REPO}/releases?per_page=20"
UPDATE_KEEP_FILES = {
    ".git",
    "__pycache__",
    "fih_config.json",
    "fih_stop.flag",
}
UPDATE_ALLOWED_SUFFIXES = {".py", ".md", ".txt"}


DEFAULT_CONFIG = {
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
    "action_gap": 0.12,
    "post_cycle_gap": 0.5,
    "min_wait_time": 10.0,
    "key_debounce": 0.25,
    "manual_input_debounce": 0.2,
    "script_input_ignore": 0.8,
    "orb_prepare_seconds": 50.0,
    "start_mode": "hype",
    "timer_mode_enabled": False,
    "orb_mode_enabled": False,
    "hotkeys": {
        "stop": "f1",
        "pause": "enter",
        "timer_mode": "f4",
        "fishing_mode": "f6",
        "orb_mode": "f7",
        "manual_override_keys": ["1", "2", "3", "4", "5", "6", "7", "8", "9"],
    },
}


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


class LauncherApp:
    def __init__(self):
        self.root = Tk()
        self.root.title("FIh Launcher")
        self.root.geometry("820x660")
        self.root.minsize(780, 600)

        self.process = None
        self.process_exit_reported = False
        self.output_queue = queue.Queue()
        self.script_state = "stopped"
        self.latest_release = None
        self.update_available = False
        self.vars = {}

        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.configure_style()

        self.config = self.load_config()
        self.create_variables()
        self.mode_status_var = StringVar(value=self.startup_mode_summary())
        self.build_ui()
        self.refresh_status()
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def configure_style(self):
        self.root.configure(bg="#f5f5f2")
        self.style.configure(".", font=("Segoe UI", 10), background="#f5f5f2")
        self.style.configure("TFrame", background="#f5f5f2")
        self.style.configure("TLabel", background="#f5f5f2", foreground="#202020")
        self.style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"))
        self.style.configure("Status.TLabel", font=("Segoe UI", 10, "bold"))
        self.style.configure("Running.Status.TLabel", font=("Segoe UI", 10, "bold"), foreground="#1f8a45")
        self.style.configure("Paused.Status.TLabel", font=("Segoe UI", 10, "bold"), foreground="#b7791f")
        self.style.configure("Stopped.Status.TLabel", font=("Segoe UI", 10, "bold"), foreground="#b83232")
        self.style.configure("Modes.TLabel", font=("Segoe UI", 9), foreground="#404040")
        self.style.configure("TButton", padding=(12, 6))
        self.style.configure("TLabelframe", background="#f5f5f2", padding=10)
        self.style.configure("TLabelframe.Label", background="#f5f5f2", font=("Segoe UI", 10, "bold"))
        self.style.configure("TNotebook", background="#f5f5f2", borderwidth=0)
        self.style.configure("TNotebook.Tab", padding=(14, 7))

    def load_config(self):
        if not CONFIG_PATH.exists():
            self.save_config(DEFAULT_CONFIG)
            return DEFAULT_CONFIG.copy()

        with CONFIG_PATH.open("r", encoding="utf-8") as handle:
            loaded = json.load(handle)

        config = merge_defaults(DEFAULT_CONFIG, loaded)
        self.save_config(config)
        return config

    def save_config(self, config=None):
        data = config if config is not None else self.config_from_variables()
        CONFIG_PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        self.config = data

    def create_variables(self):
        cfg = self.config
        hotkeys = cfg["hotkeys"]

        self.vars = {
            "start_mode": StringVar(value=cfg["start_mode"]),
            "timer_mode_enabled": BooleanVar(value=cfg["timer_mode_enabled"]),
            "orb_mode_enabled": BooleanVar(value=cfg["orb_mode_enabled"]),
            "screen_backend": StringVar(value=cfg["screen_backend"]),
            "input_backend": StringVar(value=cfg["input_backend"]),
            "tolerance": DoubleVar(value=cfg["tolerance"]),
            "poll_interval": DoubleVar(value=cfg["poll_interval"]),
            "scan_interval": DoubleVar(value=cfg["scan_interval"]),
            "action_gap": DoubleVar(value=cfg["action_gap"]),
            "post_cycle_gap": DoubleVar(value=cfg["post_cycle_gap"]),
            "min_wait_time": DoubleVar(value=cfg["min_wait_time"]),
            "key_debounce": DoubleVar(value=cfg["key_debounce"]),
            "manual_input_debounce": DoubleVar(value=cfg["manual_input_debounce"]),
            "script_input_ignore": DoubleVar(value=cfg["script_input_ignore"]),
            "orb_prepare_seconds": DoubleVar(value=cfg["orb_prepare_seconds"]),
            "rod_slot": StringVar(value=cfg["rod_slot"]),
            "weapon_slot": StringVar(value=cfg["weapon_slot"]),
            "orb_slot": StringVar(value=cfg["orb_slot"]),
            "region_left": IntVar(value=cfg["region"][0]),
            "region_top": IntVar(value=cfg["region"][1]),
            "region_width": IntVar(value=cfg["region"][2]),
            "region_height": IntVar(value=cfg["region"][3]),
            "target_r": IntVar(value=cfg["target_rgb"][0]),
            "target_g": IntVar(value=cfg["target_rgb"][1]),
            "target_b": IntVar(value=cfg["target_rgb"][2]),
            "hotkey_stop": StringVar(value=hotkeys["stop"]),
            "hotkey_pause": StringVar(value=hotkeys["pause"]),
            "hotkey_timer_mode": StringVar(value=hotkeys["timer_mode"]),
            "hotkey_fishing_mode": StringVar(value=hotkeys["fishing_mode"]),
            "hotkey_orb_mode": StringVar(value=hotkeys["orb_mode"]),
            "manual_override_keys": StringVar(value=", ".join(hotkeys["manual_override_keys"])),
        }

    def sync_variables_from_config(self):
        cfg = self.config
        hotkeys = cfg["hotkeys"]
        values = {
            "start_mode": cfg["start_mode"],
            "timer_mode_enabled": cfg["timer_mode_enabled"],
            "orb_mode_enabled": cfg["orb_mode_enabled"],
            "screen_backend": cfg["screen_backend"],
            "input_backend": cfg["input_backend"],
            "tolerance": cfg["tolerance"],
            "poll_interval": cfg["poll_interval"],
            "scan_interval": cfg["scan_interval"],
            "action_gap": cfg["action_gap"],
            "post_cycle_gap": cfg["post_cycle_gap"],
            "min_wait_time": cfg["min_wait_time"],
            "key_debounce": cfg["key_debounce"],
            "manual_input_debounce": cfg["manual_input_debounce"],
            "script_input_ignore": cfg["script_input_ignore"],
            "orb_prepare_seconds": cfg["orb_prepare_seconds"],
            "rod_slot": cfg["rod_slot"],
            "weapon_slot": cfg["weapon_slot"],
            "orb_slot": cfg["orb_slot"],
            "region_left": cfg["region"][0],
            "region_top": cfg["region"][1],
            "region_width": cfg["region"][2],
            "region_height": cfg["region"][3],
            "target_r": cfg["target_rgb"][0],
            "target_g": cfg["target_rgb"][1],
            "target_b": cfg["target_rgb"][2],
            "hotkey_stop": hotkeys["stop"],
            "hotkey_pause": hotkeys["pause"],
            "hotkey_timer_mode": hotkeys["timer_mode"],
            "hotkey_fishing_mode": hotkeys["fishing_mode"],
            "hotkey_orb_mode": hotkeys["orb_mode"],
            "manual_override_keys": ", ".join(hotkeys["manual_override_keys"]),
        }

        for key, value in values.items():
            self.vars[key].set(value)

    def build_ui(self):
        root_frame = ttk.Frame(self.root, padding=18)
        root_frame.pack(fill="both", expand=True)

        header = ttk.Frame(root_frame)
        header.pack(fill="x")

        ttk.Label(header, text=f"FIh Launcher {APP_VERSION}", style="Header.TLabel").pack(side="left")
        self.status_label = ttk.Label(header, text="Stopped", style="Stopped.Status.TLabel")
        self.status_label.pack(side="right")

        modes = ttk.Frame(root_frame)
        modes.pack(fill="x", pady=(6, 0))
        ttk.Label(modes, textvariable=self.mode_status_var, style="Modes.TLabel").pack(side="left")

        controls = ttk.Frame(root_frame)
        controls.pack(fill="x", pady=(16, 8))

        self.start_button = ttk.Button(controls, text="Start", command=self.start_script)
        self.start_button.pack(side="left")
        self.stop_button = ttk.Button(controls, text="Stop", command=self.stop_script)
        self.stop_button.pack(side="left", padx=(8, 0))

        save_button = ttk.Button(controls, text="Save", command=self.save_from_ui)
        save_button.pack(side="right")
        ToolTip(save_button, "Writes the settings shown here to fih_config.json. The running script only uses them after restart.")

        reload_button = ttk.Button(controls, text="Reload", command=self.reload_config)
        reload_button.pack(side="right", padx=(0, 8))
        ToolTip(reload_button, "Loads fih_config.json from disk and replaces the values currently shown in this window.")

        update_controls = ttk.Frame(root_frame)
        update_controls.pack(fill="x", pady=(0, 12))

        self.check_update_button = ttk.Button(update_controls, text="Check updates", command=self.check_updates_async)
        self.check_update_button.pack(side="left")
        ToolTip(self.check_update_button, "Checks GitHub Releases for a newer version. Nothing is downloaded automatically.")

        self.update_button = ttk.Button(update_controls, text="Update", command=self.install_update_async, state="disabled")
        self.update_button.pack(side="left", padx=(8, 0))
        ToolTip(self.update_button, "Downloads the newest GitHub Release and replaces local program files. Your config stays untouched.")

        self.update_label = ttk.Label(update_controls, text="Updates not checked")
        self.update_label.pack(side="left", padx=(10, 0), fill="x", expand=True)

        notebook = ttk.Notebook(root_frame)
        notebook.pack(fill="both", expand=True)

        general_tab = ttk.Frame(notebook, padding=14)
        detection_tab = ttk.Frame(notebook, padding=14)
        timing_tab = ttk.Frame(notebook, padding=14)
        hotkey_tab = ttk.Frame(notebook, padding=14)
        log_tab = ttk.Frame(notebook, padding=14)

        notebook.add(general_tab, text="General")
        notebook.add(detection_tab, text="Detection")
        notebook.add(timing_tab, text="Timing")
        notebook.add(hotkey_tab, text="Hotkeys")
        notebook.add(log_tab, text="Log")

        self.build_general_tab(general_tab)
        self.build_detection_tab(detection_tab)
        self.build_timing_tab(timing_tab)
        self.build_hotkey_tab(hotkey_tab)
        self.build_log_tab(log_tab)
        self.root.after(500, self.check_updates_async)

    def build_general_tab(self, parent):
        self.add_combo(parent, "Start mode", "start_mode", ["trophy", "hype", "flay"], 0)
        self.add_combo(parent, "Screen backend", "screen_backend", ["auto", "mss", "dxcam"], 1)
        self.add_combo(parent, "Input backend", "input_backend", ["auto", "pynput", "legacy"], 2)

        checks = ttk.LabelFrame(parent, text="Startup")
        checks.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(18, 0))
        ttk.Checkbutton(checks, text="Timer mode enabled", variable=self.vars["timer_mode_enabled"]).pack(anchor="w")
        ttk.Checkbutton(checks, text="Orb mode enabled", variable=self.vars["orb_mode_enabled"]).pack(anchor="w", pady=(8, 0))

        parent.columnconfigure(1, weight=1)

    def build_detection_tab(self, parent):
        region = ttk.LabelFrame(parent, text="Region")
        region.pack(fill="x")

        for index, (label, key) in enumerate(
            [
                ("Left", "region_left"),
                ("Top", "region_top"),
                ("Width", "region_width"),
                ("Height", "region_height"),
            ]
        ):
            self.add_entry(region, label, key, index, column=(index % 2) * 2, row=index // 2)

        color = ttk.LabelFrame(parent, text="Target Color")
        color.pack(fill="x", pady=(16, 0))

        for index, (label, key) in enumerate([("R", "target_r"), ("G", "target_g"), ("B", "target_b")]):
            self.add_entry(color, label, key, index, column=index * 2, row=0)

        tolerance = ttk.LabelFrame(parent, text="Tolerance")
        tolerance.pack(fill="x", pady=(16, 0))
        self.add_entry(tolerance, "Tolerance", "tolerance", 0)

    def build_timing_tab(self, parent):
        slot_frame = ttk.LabelFrame(parent, text="Hotbar Slots")
        slot_frame.pack(fill="x")
        self.add_entry(slot_frame, "Rod", "rod_slot", 0, column=0, row=0)
        self.add_entry(slot_frame, "Weapon", "weapon_slot", 1, column=2, row=0)
        self.add_entry(slot_frame, "Orb", "orb_slot", 2, column=4, row=0)

        timing_frame = ttk.LabelFrame(parent, text="Timing")
        timing_frame.pack(fill="x", pady=(16, 0))
        fields = [
            ("Poll interval", "poll_interval"),
            ("Scan interval", "scan_interval"),
            ("Action gap", "action_gap"),
            ("Post cycle gap", "post_cycle_gap"),
            ("Min wait time", "min_wait_time"),
            ("Orb prepare seconds", "orb_prepare_seconds"),
            ("Key debounce", "key_debounce"),
            ("Manual input debounce", "manual_input_debounce"),
            ("Script input ignore", "script_input_ignore"),
        ]
        for index, (label, key) in enumerate(fields):
            self.add_entry(timing_frame, label, key, index, column=(index % 2) * 2, row=index // 2)

    def build_hotkey_tab(self, parent):
        fields = [
            ("Stop", "hotkey_stop"),
            ("Pause", "hotkey_pause"),
            ("Timer mode", "hotkey_timer_mode"),
            ("Fishing mode", "hotkey_fishing_mode"),
            ("Orb mode", "hotkey_orb_mode"),
            ("Manual override keys", "manual_override_keys"),
        ]
        for index, (label, key) in enumerate(fields):
            self.add_entry(parent, label, key, index)
        parent.columnconfigure(1, weight=1)

    def build_log_tab(self, parent):
        self.output = TextWithScrollbar(parent)
        self.output.frame.pack(fill="both", expand=True)

    def add_combo(self, parent, label, key, values, row):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=6)
        combo = ttk.Combobox(parent, textvariable=self.vars[key], values=values, state="readonly")
        combo.grid(row=row, column=1, sticky="ew", pady=6, padx=(12, 0))

    def add_entry(self, parent, label, key, index, column=0, row=None, pady=6):
        row = index if row is None else row
        ttk.Label(parent, text=label).grid(row=row, column=column, sticky="w", pady=pady, padx=(0, 8))
        ttk.Entry(parent, textvariable=self.vars[key], width=18).grid(row=row, column=column + 1, sticky="ew", pady=pady, padx=(0, 18))
        parent.columnconfigure(column + 1, weight=1)

    @staticmethod
    def on_off(value):
        return "ON" if value else "OFF"

    def startup_mode_summary(self):
        return (
            f"Startup modes: Fishing {self.config['start_mode'].upper()} | "
            f"Timer {self.on_off(self.config['timer_mode_enabled'])} | "
            f"Orb {self.on_off(self.config['orb_mode_enabled'])}"
        )

    @staticmethod
    def live_mode_summary(raw_status):
        parts = dict(re.findall(r"([A-Za-z]+)=([^|]+)", raw_status))
        fishing = parts.get("Fishing", "?").strip().upper()
        timer = parts.get("Timer", "?").strip().upper()
        orb = parts.get("Orb", "?").strip().upper()
        pending = parts.get("OrbPending", "?").strip().upper()
        return f"Live modes: Fishing {fishing} | Timer {timer} | Orb {orb} | Orb pending {pending}"

    def config_from_variables(self):
        manual_keys = [
            key.strip()
            for key in self.vars["manual_override_keys"].get().split(",")
            if key.strip()
        ]

        return {
            "region": [
                self.vars["region_left"].get(),
                self.vars["region_top"].get(),
                self.vars["region_width"].get(),
                self.vars["region_height"].get(),
            ],
            "target_rgb": [
                self.vars["target_r"].get(),
                self.vars["target_g"].get(),
                self.vars["target_b"].get(),
            ],
            "tolerance": self.vars["tolerance"].get(),
            "screen_backend": self.vars["screen_backend"].get(),
            "input_backend": self.vars["input_backend"].get(),
            "rod_slot": self.vars["rod_slot"].get(),
            "weapon_slot": self.vars["weapon_slot"].get(),
            "orb_slot": self.vars["orb_slot"].get(),
            "poll_interval": self.vars["poll_interval"].get(),
            "scan_interval": self.vars["scan_interval"].get(),
            "action_gap": self.vars["action_gap"].get(),
            "post_cycle_gap": self.vars["post_cycle_gap"].get(),
            "min_wait_time": self.vars["min_wait_time"].get(),
            "key_debounce": self.vars["key_debounce"].get(),
            "manual_input_debounce": self.vars["manual_input_debounce"].get(),
            "script_input_ignore": self.vars["script_input_ignore"].get(),
            "orb_prepare_seconds": self.vars["orb_prepare_seconds"].get(),
            "start_mode": self.vars["start_mode"].get(),
            "timer_mode_enabled": self.vars["timer_mode_enabled"].get(),
            "orb_mode_enabled": self.vars["orb_mode_enabled"].get(),
            "hotkeys": {
                "stop": self.vars["hotkey_stop"].get(),
                "pause": self.vars["hotkey_pause"].get(),
                "timer_mode": self.vars["hotkey_timer_mode"].get(),
                "fishing_mode": self.vars["hotkey_fishing_mode"].get(),
                "orb_mode": self.vars["hotkey_orb_mode"].get(),
                "manual_override_keys": manual_keys,
            },
        }

    def save_from_ui(self):
        try:
            self.save_config()
        except Exception as exc:
            messagebox.showerror("Save failed", str(exc))
            return
        self.mode_status_var.set(self.startup_mode_summary())
        self.log("Config saved.")

    def reload_config(self):
        self.config = self.load_config()
        self.sync_variables_from_config()
        self.mode_status_var.set(self.startup_mode_summary())
        self.log("Config reloaded.")

    def check_updates_async(self):
        self.check_update_button.configure(state="disabled")
        self.update_label.configure(text="Checking updates...")
        threading.Thread(target=self.check_updates_worker, daemon=True).start()

    def check_updates_worker(self):
        try:
            release = fetch_latest_release()
            latest_version = release["tag_name"]
            is_newer = version_is_newer(latest_version, APP_VERSION)
        except Exception as exc:
            self.root.after(0, lambda: self.show_update_error(exc))
            return

        self.root.after(0, lambda: self.show_update_result(release, is_newer))

    def show_update_result(self, release, is_newer):
        self.latest_release = release
        self.update_available = is_newer
        self.check_update_button.configure(state="normal")

        latest_version = release["tag_name"]
        release_kind = "pre-release" if release.get("prerelease") else "release"
        if is_newer:
            message = f"Found {latest_version} ({release_kind}). Update available."
            self.update_label.configure(text=message)
            self.update_button.configure(state="normal")
        elif same_version(latest_version, APP_VERSION):
            message = f"Found {latest_version} ({release_kind}). You are up to date."
            self.update_label.configure(text=message)
            self.update_button.configure(state="disabled")
        else:
            message = f"Found {latest_version} ({release_kind}). Local version {APP_VERSION} is newer."
            self.update_label.configure(text=message)
            self.update_button.configure(state="disabled")

        self.log(message)

    def show_update_error(self, exc):
        self.check_update_button.configure(state="normal")
        self.update_button.configure(state="disabled")
        self.update_label.configure(text=str(exc))
        self.log(f"Update check failed: {exc}")

    def install_update_async(self):
        if not self.latest_release or not self.update_available:
            return

        if self.process and self.process.poll() is None:
            answer = messagebox.askyesno(
                "Stop FIh?",
                "FIh must be stopped before updating. Stop it now?",
            )
            if not answer:
                return
            self.terminate_script()

        self.update_button.configure(state="disabled")
        self.check_update_button.configure(state="disabled")
        self.update_label.configure(text=f"Installing {self.latest_release['tag_name']}...")
        threading.Thread(target=self.install_update_worker, daemon=True).start()

    def install_update_worker(self):
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
                copy_update_files(source_dir, APP_DIR)
        except Exception as exc:
            self.root.after(0, lambda: self.show_install_error(exc))
            return

        self.root.after(0, self.show_install_success)

    def show_install_success(self):
        version = self.latest_release["tag_name"]
        self.update_label.configure(text=f"Installed {version}. Restart launcher.")
        self.check_update_button.configure(state="normal")
        self.log(f"Installed {version}. Restart the launcher to run the new version.")
        messagebox.showinfo(
            "Update installed",
            "Update installed. Please close and restart the launcher so the new launcher code is loaded.",
        )

    def show_install_error(self, exc):
        self.update_label.configure(text="Update failed")
        self.check_update_button.configure(state="normal")
        self.update_button.configure(state="normal" if self.update_available else "disabled")
        self.log(f"Update failed: {exc}")
        messagebox.showerror("Update failed", str(exc))

    def start_script(self):
        if self.process and self.process.poll() is None:
            return

        self.save_config()
        STOP_PATH.unlink(missing_ok=True)
        self.process = subprocess.Popen(
            [sys.executable, "-u", str(SCRIPT_PATH)],
            cwd=str(APP_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        self.process_exit_reported = False
        threading.Thread(target=self.read_process_output, daemon=True).start()
        self.set_state("running")
        self.mode_status_var.set("Live modes: waiting for script status...")
        self.log("Started FIh.")

    def stop_script(self):
        if self.terminate_script():
            self.log("Stop requested.")

    def read_process_output(self):
        if not self.process or not self.process.stdout:
            return
        for line in self.process.stdout:
            self.output_queue.put(line.rstrip())

    def refresh_status(self):
        while not self.output_queue.empty():
            message = self.output_queue.get()
            self.update_state_from_output(message)
            self.log(message)

        running = self.process is not None and self.process.poll() is None
        if not running:
            if self.process is not None and not self.process_exit_reported:
                self.log(f"FIh exited with code {self.process.returncode}.")
                self.process_exit_reported = True
            self.set_state("stopped")

        self.start_button.configure(state="disabled" if running else "normal")
        self.stop_button.configure(state="normal" if running else "disabled")
        self.root.after(250, self.refresh_status)

    def update_state_from_output(self, message):
        if "--> Modi:" in message:
            raw_status = message.split("--> Modi:", 1)[1].strip()
            self.mode_status_var.set(self.live_mode_summary(raw_status))

        if "--> PAUSE" in message:
            self.set_state("paused")
        elif "--> Weiter" in message:
            self.set_state("running")
        elif message.strip() == "Beende...":
            self.set_state("stopped")

    def set_state(self, state):
        self.script_state = state
        labels = {
            "running": ("Running", "Running.Status.TLabel"),
            "paused": ("Paused", "Paused.Status.TLabel"),
            "stopped": ("Stopped", "Stopped.Status.TLabel"),
        }
        text, style = labels[state]
        self.status_label.configure(text=text, style=style)

    def log(self, message):
        if hasattr(self, "output"):
            self.output.append(message)

    def terminate_script(self):
        if not self.process or self.process.poll() is not None:
            self.set_state("stopped")
            return False

        STOP_PATH.write_text("stop\n", encoding="utf-8")
        try:
            self.process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=2)

        STOP_PATH.unlink(missing_ok=True)

        try:
            self.process.stdout.close()
        except AttributeError:
            pass

        self.set_state("stopped")
        return True

    def force_terminate_script(self):
        if not self.process or self.process.poll() is not None:
            return False

        self.process.terminate()
        try:
            self.process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=2)

        self.set_state("stopped")
        return True

    def close(self):
        self.terminate_script()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


class TextWithScrollbar:
    def __init__(self, parent):
        from tkinter import Text

        self.frame = ttk.Frame(parent)
        self.text = Text(self.frame, height=12, wrap="word", borderwidth=0, padx=10, pady=10)
        scrollbar = ttk.Scrollbar(self.frame, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=scrollbar.set)
        self.text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def append(self, message):
        self.text.configure(state="normal")
        self.text.insert("end", message + "\n")
        self.text.see("end")
        self.text.configure(state="disabled")


def fetch_latest_release():
    request = urllib.request.Request(
        RELEASES_API_URL,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"sidechick-launcher/{APP_VERSION}",
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
    parts = re.findall(r"\d+", cleaned)
    return tuple(int(part) for part in parts[:3])


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
    url = release_download_url(release)
    request = urllib.request.Request(
        url,
        headers={"User-Agent": f"sidechick-launcher/{APP_VERSION}"},
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
    if any(part in UPDATE_KEEP_FILES for part in path.parts):
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


class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip = None
        self.widget.bind("<Enter>", self.show)
        self.widget.bind("<Leave>", self.hide)

    def show(self, _event=None):
        if self.tip is not None:
            return

        x = self.widget.winfo_rootx() + 12
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 8
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")

        label = tk.Label(
            self.tip,
            text=self.text,
            justify="left",
            background="#252525",
            foreground="#f7f7f7",
            relief="solid",
            borderwidth=1,
            padx=8,
            pady=6,
            wraplength=320,
            font=("Segoe UI", 9),
        )
        label.pack()

    def hide(self, _event=None):
        if self.tip is not None:
            self.tip.destroy()
            self.tip = None


if __name__ == "__main__":
    LauncherApp().run()
