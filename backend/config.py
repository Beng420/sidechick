import copy
import json
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = APP_DIR / "configs"
APP_CONFIG_PATH = CONFIG_DIR / "sidechick.json"
LEGACY_FIH_CONFIG_PATH = APP_DIR / "fih_config.json"
APP_VERSION = "v1.8.8"
UPDATE_REPO = "Beng420/sidechick"


APP_DEFAULT_CONFIG = {
    "config_version": 1,
    "selected_script": "fih",
    "theme": "dark",
}


FIH_DEFAULT_CONFIG = {
    "config_version": 5,
    "region": [1519, 724, 17, 50],
    "target_rgb": [252, 84, 84],
    "tolerance": 20.0,
    "screen_backend": "auto",
    "input_backend": "auto",
    "rod_slot": ["4"],
    "weapon_slot": ["3"],
    "orb_slot": ["5"],
    "poll_interval": 0.05,
    "scan_interval": 0.12,
    "action_gap": 0.10,
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
        "stop": ["f1"],
        "pause": ["enter"],
        "timer_mode": ["f4"],
        "fishing_mode": ["f6"],
        "orb_mode": ["f7"],
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
    "pre_click_delay": 0.50,
    "move_back_position": [700, 300],
    "toggle_hotkey": ["f1"],
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
                    {"key": "find_region", "label": "Coordinate search", "type": "action", "action": "find_fih_region"},
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
                    {"key": "hotkeys.stop", "label": "Stop", "type": "bindings"},
                    {"key": "hotkeys.pause", "label": "Pause", "type": "bindings"},
                    {"key": "hotkeys.timer_mode", "label": "Timer mode", "type": "bindings"},
                    {"key": "hotkeys.fishing_mode", "label": "Fishing mode", "type": "bindings"},
                    {"key": "hotkeys.orb_mode", "label": "Orb mode", "type": "bindings"},
                    {"key": "hotkeys.manual_override_keys", "label": "Manual keys", "type": "bindings"},
                    {"key": "hotkeys.manual_override_mouse_buttons", "label": "Manual mouse buttons", "type": "bindings"},
                ],
            },
            {
                "title": "Slots",
                "fields": [
                    {"key": "rod_slot", "label": "Rod slot", "type": "bindings"},
                    {"key": "weapon_slot", "label": "Weapon slot", "type": "bindings"},
                    {"key": "orb_slot", "label": "Orb slot", "type": "bindings"},
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
                    {"key": "pre_click_delay", "label": "Pre-click delay", "type": "float"},
                    {"key": "move_back_position", "label": "Move-back position", "type": "json"},
                ],
            },
            {
                "title": "Hotkeys",
                "fields": [
                    {"key": "toggle_hotkey", "label": "Pause/resume", "type": "bindings"},
                    {"key": "hotkeys_enabled", "label": "Script hotkeys", "type": "bool"},
                ],
            },
        ],
    },
}


SETTING_HELP = {
    "fih": {
        "start_mode": "Legt fest, mit welchem Fishing-Ablauf FIh startet. Trophy wirft nur die Angel, Hype und Flay nutzen zusaetzlich das eingestellte Item.",
        "screen_backend": "Waehlt, womit FIh den Bildschirm ausliest. Auto/mss ist der stabile Standard; dxcam ist eine Windows-Option zum Experimentieren.",
        "input_backend": "Waehlt, womit FIh Tasten und Maus ausgibt und Hotkeys erkennt. Auto nimmt den passenden Standard fuer dein System.",
        "timer_mode_enabled": "Wenn aktiv, wartet FIh mindestens die eingestellte Zeit, bevor ein neuer Ablauf startet. Das verhindert zu schnelle Wiederholungen bei Timer-Spielweisen.",
        "orb_mode_enabled": "Wenn aktiv, plant FIh regelmaessig einen Orb ein und setzt ihn im naechsten passenden Ablauf. Orb Pending zeigt, ob gerade ein Orb vorgemerkt ist.",
        "hotkeys_enabled": "Schaltet die Hotkeys dieses Scripts ein oder aus. Der Launcher deaktiviert andere Script-Hotkeys automatisch, wenn du ein anderes Script auswaehlst.",
        "region.0": "Linke X-Koordinate des kleinen Bildschirmbereichs, in dem FIh nach der Bissfarbe sucht. Verschiebe sie, wenn die Erkennung links oder rechts daneben liegt.",
        "region.1": "Obere Y-Koordinate des Suchbereichs fuer die Bissfarbe. Verschiebe sie, wenn die rote Anzeige hoeher oder tiefer sitzt.",
        "region.2": "Breite des Suchbereichs in Pixeln. Groesser ist toleranter, aber kann eher fremde Farben mitnehmen.",
        "region.3": "Hoehe des Suchbereichs in Pixeln. Groesser hilft bei schwankender Anzeige, kleiner ist praeziser.",
        "target_rgb.0": "Rotwert der Farbe, die als Biss erkannt wird. Normalerweise muss dieser Wert nur angepasst werden, wenn dein Spiel/Shader anders aussieht.",
        "target_rgb.1": "Gruenwert der Bissfarbe. Zusammen mit Rot und Blau bildet er die Zielfarbe fuer die Erkennung.",
        "target_rgb.2": "Blauwert der Bissfarbe. Zusammen mit Rot und Gruen bildet er die Zielfarbe fuer die Erkennung.",
        "tolerance": "Erlaubte Abweichung von der Zielfarbe. Hoeher erkennt mehr Varianten, kann aber auch falsche Treffer verursachen.",
        "find_region": "Startet eine Kalibrierung fuer die Region-Koordinaten. Jeder Linksklick setzt die markierte Position neu; mit Escape oder Cancel kannst du die Suche abbrechen.",
        "scan_interval": "Zeit zwischen zwei Farbpruefungen, solange kein Ablauf laeuft. Niedriger reagiert schneller, braucht aber mehr CPU.",
        "action_gap": "Pause zwischen einzelnen Aktionen im FIh-Ablauf, zum Beispiel Slot wechseln und Rechtsklick. Erhoehe den Wert, wenn das Spiel Eingaben verschluckt.",
        "post_cycle_gap": "Wartezeit nach dem letzten Auswerfen, bevor FIh wieder scannt. Hilft gegen doppelte Ablaufe direkt nach einem Cast.",
        "min_wait_time": "Mindestzeit seit dem letzten Auswerfen, wenn Timer Mode aktiv ist. FIh startet erst danach wieder einen Ablauf.",
        "orb_prepare_seconds": "Zeit, nach der ein neuer Orb vorgemerkt wird. Sobald die Zeit vorbei ist, setzt FIh den Orb beim naechsten passenden Ablauf.",
        "script_input_ignore": "Zeitfenster, in dem FIh seine eigenen Tasten/Mausaktionen nicht als manuellen Eingriff wertet. Erhoehe es, wenn eigene Script-Klicks faelschlich abbrechen.",
        "hotkeys.stop": "Hotkeys zum sofortigen Beenden des Scripts. Mehrere Belegungen kannst du mit Kommas trennen.",
        "hotkeys.pause": "Hotkeys zum Pausieren und Fortsetzen. Mehrere Belegungen kannst du mit Kommas trennen.",
        "hotkeys.timer_mode": "Hotkeys zum Umschalten des Timer Mode. Mehrere Belegungen kannst du mit Kommas trennen.",
        "hotkeys.fishing_mode": "Hotkeys zum Durchschalten der Fishing-Modi Trophy, Hype und Flay. Mehrere Belegungen kannst du mit Kommas trennen.",
        "hotkeys.orb_mode": "Hotkeys zum Ein- und Ausschalten des Orb Mode. Mehrere Belegungen kannst du mit Kommas trennen.",
        "hotkeys.manual_override_keys": "Tasten, die als manueller Eingriff gelten und den laufenden Ablauf abbrechen. Das ist praktisch, wenn du selbst eingreifen willst.",
        "hotkeys.manual_override_mouse_buttons": "Mausbuttons, die als manueller Eingriff gelten und den laufenden Ablauf abbrechen. Der Script-eigene Rechtsklick wird dabei ignoriert.",
        "rod_slot": "Taste oder Mausbutton fuer den Angel-Slot. Der erste Eintrag wird vom Script gedrueckt; weitere Eintraege bleiben als Alternative in deiner Config.",
        "weapon_slot": "Taste oder Mausbutton fuer das Item/Weapon-Slot im Hype- oder Flay-Ablauf. Der erste Eintrag wird vom Script gedrueckt.",
        "orb_slot": "Taste oder Mausbutton fuer den Orb-Slot. Der erste Eintrag wird genutzt, wenn FIh im Orb Mode einen Orb setzen soll.",
    },
    "superpairs": {
        "start_x": "X-Koordinate der ersten Karte oben links im Superpairs-Feld. Von hier aus werden alle weiteren Kartenpositionen berechnet.",
        "start_y": "Y-Koordinate der ersten Karte oben links im Superpairs-Feld. Von hier aus werden alle weiteren Kartenpositionen berechnet.",
        "horizontal_gap": "Horizontaler Abstand zwischen zwei Kartenmittelpunkten in Pixeln. Passe ihn an, wenn Klicks links oder rechts neben den Karten landen.",
        "vertical_gap": "Vertikaler Abstand zwischen zwei Kartenmittelpunkten in Pixeln. Passe ihn an, wenn Klicks ueber oder unter den Karten landen.",
        "columns": "Anzahl der Karten-Spalten im Superpairs-Feld. Muss zum sichtbaren Board passen, sonst scannt das Script falsche Positionen.",
        "rows": "Anzahl der Karten-Reihen im Superpairs-Feld. Muss zum sichtbaren Board passen, sonst scannt das Script falsche Positionen.",
        "target_colors": "Liste der RGB-Farben, die Superpairs als Treffer erkennt. Du kannst mehrere Farben eintragen, wenn die Karte leicht verschiedene Gruentoene hat.",
        "tolerance": "Erlaubte Farbabweichung fuer Superpairs-Treffer. Hoeher erkennt mehr Varianten, kann aber auch falsche Pixel treffen.",
        "scan_interval": "Zeit zwischen zwei Board-Scans. Niedriger reagiert schneller, hoeher ist ruhiger und spart CPU.",
        "click_cooldown": "Mindestpause zwischen zwei Klicks. Erhoehe den Wert, wenn Superpairs noch zu schnell mehrfach klickt.",
        "pre_click_delay": "Wartezeit nachdem die Maus von der Karte wegbewegt wurde und bevor sie zur Karte zurueckgeht. Standard ist 0.5 Sekunden.",
        "move_back_position": "Position, zu der die Maus nach dem Klick und vor dem naechsten Klick bewegt wird. Waehle eine Stelle, die keine Karten verdeckt.",
        "toggle_hotkey": "Hotkeys zum Pausieren und Fortsetzen von Superpairs. Mehrere Belegungen kannst du mit Kommas trennen.",
        "hotkeys_enabled": "Schaltet die Superpairs-Hotkeys ein oder aus. Der Launcher kann Superpairs trotzdem ueber die Buttons steuern.",
    },
}


def attach_setting_help():
    for script_id, help_by_key in SETTING_HELP.items():
        for group in SCRIPT_DEFINITIONS[script_id]["schema"]:
            for field in group["fields"]:
                help_text = help_by_key.get(field["key"])
                if help_text:
                    field["help"] = help_text


attach_setting_help()


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

    config = normalize_script_config(script_id, merge_defaults(script["default_config"], loaded))
    write_json(path, config)
    return config


def save_script_config(script_id, config):
    script = SCRIPT_DEFINITIONS[script_id]
    data = normalize_script_config(script_id, merge_defaults(script["default_config"], config))
    write_json(script["config_path"], data)
    return data


def binding_list(value):
    if isinstance(value, list):
        raw_values = value
    else:
        raw_values = str(value or "").split(",")

    bindings = []
    for item in raw_values:
        binding = str(item).strip()
        if binding and binding not in bindings:
            bindings.append(binding)
    return bindings


def normalize_script_config(script_id, config):
    if script_id == "fih":
        config_version = int(config.get("config_version", 1))
        if config_version < 5 and float(config.get("action_gap", 0.10)) == 0.03:
            config["action_gap"] = FIH_DEFAULT_CONFIG["action_gap"]
        config["config_version"] = FIH_DEFAULT_CONFIG["config_version"]
        for key in ("rod_slot", "weapon_slot", "orb_slot"):
            config[key] = binding_list(config.get(key))
        hotkeys = config.get("hotkeys", {})
        for key in ("stop", "pause", "timer_mode", "fishing_mode", "orb_mode"):
            hotkeys[key] = binding_list(hotkeys.get(key))
        for key in ("manual_override_keys", "manual_override_mouse_buttons"):
            hotkeys[key] = binding_list(hotkeys.get(key))
        config["hotkeys"] = hotkeys
    elif script_id == "superpairs":
        config["toggle_hotkey"] = binding_list(config.get("toggle_hotkey")) or binding_list(
            SUPERPAIRS_DEFAULT_CONFIG["toggle_hotkey"]
        )
    return config


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
