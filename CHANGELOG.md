# Changelog

## v1.2

- Fishing-Ablauf in einzelne Schritte aufgeteilt, damit Pause/Fortsetzen zwischen Aktionen sauber funktioniert.
- Manueller Eingriff erkannt: eigener Rechtsklick oder Zahlenhotkeys verwerfen den laufenden Ablauf und warten auf den naechsten Biss.
- Einstellungen in `fih_config.json` ausgelagert, inklusive Hotkeys, Slots, Timing, Startmodus und Backend-Auswahl.
- Config wird beim ersten Start automatisch erstellt und spaeter wieder geladen.
- Screenshot-Erkennung optimiert: `mss`/`numpy` statt `pyautogui.screenshot()`/PIL, mit einstellbarem `scan_interval`.
- Plattformfreundlichere Backends vorbereitet: `mss` als Standard, optional `dxcam` auf Windows, `pynput` bevorzugt fuer Mac-Input.
- `requirements.txt` hinzugefuegt, damit benoetigte Pakete einfacher installiert werden koennen.
