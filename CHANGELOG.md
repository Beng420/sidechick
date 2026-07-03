# Changelog

## v1.8.3

- Added marked-position feedback and a temporary crosshair overlay during FIh coordinate search.
- Changed the default Sidechick window size to give settings more room.
- Changed FIh bite detection to react to matching pixels inside the region instead of averaging the whole region color.
- Fixed FIh getting stuck waiting for the bite color to reset after manual input.

## v1.8.2

- Added coordinate search for FIh region calibration.
- Changed the default FIh action gap to `0.10`.
- Changed old FIh configs that still used the previous default action gap to the new default.

## v1.8.1

- Added automatic update checks when Sidechick starts.
- Added a red `Update available!` indicator next to the Update button when a newer release is found.
- Kept automatic update checks quiet in the log unless the user manually runs the check and it fails.

## v1.8.0

- Added mouse-following setting tooltips for every FIh and Superpairs option.
- Added multi-binding support for all FIh hotkeys, matching the existing comma-separated Manual Keys behavior.
- Added Set buttons and full binding support for FIh slot settings.
- Added broader binding capture for numpad keys, modifier keys, special keys, German characters, punctuation keys, and mouse buttons.
- Changed Superpairs to move the mouse away, wait before clicking, move back to the matched pixel, click, and then move away again.
- Added configurable Superpairs pre-click delay.
- Added multi-binding support for the Superpairs pause/resume hotkey.
- Added a dependency-install prompt when Sidechick cannot open because pywebview is missing.
- Added a post-update changelog popup that shows GitHub release notes after restarting into the updated version.

## v1.7.0

- Added parallel runtime support so FIh and Superpairs can run at the same time.
- Added Sidechick runtime pause/resume controls per script.
- Starting one script now pauses other running scripts automatically.
- Runtime hotkeys now belong to the selected script only.
- Added FIh status-card controls for fishing mode, timer mode, and orb mode.
- Added launcher-to-script runtime commands so FIh mode changes apply without restarting the script.
- Added per-script option to disable script-owned hotkeys when hotkeys conflict.

## v1.6.0

- Rebuilt Sidechick as a pywebview app with a Python backend and HTML/CSS/JS frontend.
- Added per-script config files under `configs/`.
- Added dynamic per-script settings in the UI.
- Added colored runtime status cards.

## v1.5.0

- Renamed the app entry file to `sidechick.pyw`.
- Added a Sidechick script selector with FIh and Superpairs support.
- Added a left script drawer, dark mode, and a compact FIh mode status grid.
- Added an Install requirements button.
- Added configurable pause hotkey lists and mouse button bindings.
- Changed app file type from .py to .pyw so theres no console window being opened alongside it.

## v1.4.2

- Added Overlay for fishing mode, timer mode and orb mode
- Fixed Orb mode not working outside of Hype mode

## v1.4.1

- Update check now reports the release version found on GitHub, even when local Sidechick is already up to date.
- Update check now includes pre-releases, so test releases are visible while the project is still early.

## v1.4.0

- Added GitHub Release update checks in Sidechick.
- Added an Update button that downloads and installs the newest release on demand.
- Kept `fih_config.json` local during updates so user settings are not overwritten.
- Renamed the main script to stable `fih.py` so future updates can replace files reliably.

## v1.3.0

- Added a Sidechick UI for editing config values and starting/stopping FIh.
- Added Running/Paused/Stopped status display.
- Added Save/Reload tooltips.
- Fixed Sidechick status switching to Stopped incorrectly.
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
