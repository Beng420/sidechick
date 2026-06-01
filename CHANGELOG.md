# Changelog

## v1.4.0

- Added GitHub Release update checks in the launcher.
- Added an Update button that downloads and installs the newest release on demand.
- Kept `fih_config.json` local during updates so user settings are not overwritten.
- Renamed the main script to stable `fih.py` so future updates can replace files reliably.

## v1.3.0

- Added a launcher UI for editing config values and starting/stopping FIh.
- Added Running/Paused/Stopped status display.
- Added Save/Reload tooltips.
- Fixed launcher status switching to Stopped incorrectly.
- Fixed script-generated key presses being treated as manual override input.
- Improved Windows input backend selection.

## v1.2

- Fishing-Ablauf in einzelne Schritte aufgeteilt, damit Pause/Fortsetzen zwischen Aktionen sauber funktioniert.
- Manueller Eingriff erkannt: eigener Rechtsklick oder Zahlenhotkeys verwerfen den laufenden Ablauf und warten auf den naechsten Biss.
- Einstellungen in `fih_config.json` ausgelagert, inklusive Hotkeys, Slots, Timing, Startmodus und Backend-Auswahl.
- Config wird beim ersten Start automatisch erstellt und spaeter wieder geladen.
- Screenshot-Erkennung optimiert: `mss`/`numpy` statt `pyautogui.screenshot()`/PIL, mit einstellbarem `scan_interval`.
- Plattformfreundlichere Backends vorbereitet: `mss` als Standard, optional `dxcam` auf Windows, `pynput` bevorzugt fuer Mac-Input.
- `requirements.txt` hinzugefuegt, damit benoetigte Pakete einfacher installiert werden koennen.
