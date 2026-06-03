import queue
import re
import subprocess
import sys
import threading
import time
import json

from .config import APP_DIR, SCRIPT_DEFINITIONS


def default_mode_cards():
    return {
        "fishing": "UNKNOWN",
        "timer": "OFF",
        "orb": "OFF",
        "placement": "OFF",
    }


class ScriptProcess:
    def __init__(self, script_id):
        self.process = None
        self.script_id = script_id
        self.output_queue = queue.Queue()
        self.logs = []
        self.state = "stopped"
        self.mode_cards = default_mode_cards()

    def start(self):
        if self.is_running():
            return {"ok": False, "message": "Script is already running."}

        script = SCRIPT_DEFINITIONS[self.script_id]
        if not script["script_path"].exists():
            return {"ok": False, "message": f"{script['name']} was not found."}

        script["stop_path"].unlink(missing_ok=True)
        script["control_path"].unlink(missing_ok=True)
        self.process = subprocess.Popen(
            [sys.executable, "-u", str(script["script_path"])],
            cwd=str(APP_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        self.state = "running"
        self.logs.append(f"Started {script['name']}.")
        threading.Thread(target=self._read_output, daemon=True).start()
        return {"ok": True, "message": f"Started {script['name']}."}

    def stop(self):
        if not self.process or self.process.poll() is not None:
            self.state = "stopped"
            return {"ok": False, "message": "No script is running."}

        script = SCRIPT_DEFINITIONS[self.script_id]
        script["stop_path"].write_text("stop\n", encoding="utf-8")
        self.send_command("stop")
        try:
            self.process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=2)

        script["stop_path"].unlink(missing_ok=True)
        script["control_path"].unlink(missing_ok=True)
        self.state = "stopped"
        self.logs.append(f"Stopped {script['name']}.")
        return {"ok": True, "message": "Stopped."}

    def pause(self, paused=None):
        if not self.is_running():
            return {"ok": False, "message": "No script is running."}

        if paused is None:
            paused = self.state != "paused"

        command = "pause" if paused else "resume"
        self.send_command(command)
        self.state = "paused" if paused else "running"
        return {"ok": True, "message": "Paused." if paused else "Resumed."}

    def set_runtime_state(self, paused=None, hotkeys_enabled=None):
        if not self.is_running():
            return {"ok": False, "message": "No script is running."}

        payload = {}
        if paused is not None:
            payload["paused"] = bool(paused)
            self.state = "paused" if paused else "running"
        if hotkeys_enabled is not None:
            payload["hotkeys_enabled"] = bool(hotkeys_enabled)

        if not payload:
            return {"ok": True, "message": "No runtime changes."}

        self.send_command("set_runtime_state", **payload)
        return {"ok": True, "message": "Runtime state updated."}

    def send_command(self, command, **payload):
        script = SCRIPT_DEFINITIONS[self.script_id]
        data = {
            "command": command,
            "created_at": time.time(),
            **payload,
        }
        script["control_path"].write_text(json.dumps(data), encoding="utf-8")

    def is_running(self):
        return self.process is not None and self.process.poll() is None

    def poll(self):
        while not self.output_queue.empty():
            line = self.output_queue.get()
            self.logs.append(line)
            self._parse_line(line)

        if self.process is not None and self.process.poll() is not None:
            if self.state != "stopped":
                name = SCRIPT_DEFINITIONS[self.script_id]["name"]
                self.logs.append(f"{name} exited with code {self.process.returncode}.")
            self.state = "stopped"

        return {
            "running": self.is_running(),
            "script_id": self.script_id,
            "state": self.state,
            "mode_cards": self.mode_cards.copy(),
            "logs": self.logs[-250:],
        }

    def drain_logs(self):
        self.poll()
        logs = self.logs[:]
        self.logs.clear()
        return logs

    def _read_output(self):
        if not self.process or not self.process.stdout:
            return
        for line in self.process.stdout:
            self.output_queue.put(line.rstrip())

    def _parse_line(self, line):
        if "--> PAUSE" in line or "paused" in line.lower():
            self.state = "paused"
        elif "--> Weiter" in line or "running" in line.lower():
            self.state = "running"
        elif "Beende..." in line or "stopping" in line.lower():
            self.state = "stopped"

        if "--> Modi:" in line:
            raw_status = line.split("--> Modi:", 1)[1].strip()
            parts = dict(re.findall(r"([A-Za-z]+)=([^|]+)", raw_status))
            self.mode_cards["fishing"] = parts.get("Fishing", self.mode_cards["fishing"]).strip().upper()
            self.mode_cards["timer"] = parts.get("Timer", self.mode_cards["timer"]).strip().upper()
            self.mode_cards["orb"] = parts.get("Orb", self.mode_cards["orb"]).strip().upper()
            pending = parts.get("OrbPending", "").strip().upper()
            self.mode_cards["placement"] = "PENDING" if pending in {"YES", "TRUE", "1"} else "READY"

    def close(self):
        self.stop()
        time.sleep(0.05)


class ProcessRunner:
    def __init__(self):
        self.processes = {
            script_id: ScriptProcess(script_id)
            for script_id in SCRIPT_DEFINITIONS
        }

    def start(self, script_id):
        return self.processes[script_id].start()

    def stop(self, script_id):
        return self.processes[script_id].stop()

    def pause(self, script_id, paused=None):
        return self.processes[script_id].pause(paused)

    def set_runtime_state(self, script_id, paused=None, hotkeys_enabled=None):
        return self.processes[script_id].set_runtime_state(paused, hotkeys_enabled)

    def send_command(self, script_id, command, **payload):
        if not self.processes[script_id].is_running():
            return {"ok": False, "message": "Script is not running."}
        self.processes[script_id].send_command(command, **payload)
        return {"ok": True, "message": "Command sent."}

    def is_running(self, script_id=None):
        if script_id is not None:
            return self.processes[script_id].is_running()
        return any(process.is_running() for process in self.processes.values())

    def poll(self, selected_script=None):
        states = {
            script_id: process.poll()
            for script_id, process in self.processes.items()
        }
        selected_script = selected_script or next(iter(self.processes))
        selected = states[selected_script].copy()
        selected["processes"] = states
        return selected

    def drain_logs(self, script_id=None):
        if script_id:
            return self.processes[script_id].drain_logs()

        logs = []
        for process_id, process in self.processes.items():
            name = SCRIPT_DEFINITIONS[process_id]["name"]
            logs.extend(f"[{name}] {line}" for line in process.drain_logs())
        return logs

    def close(self):
        for process in self.processes.values():
            process.close()
