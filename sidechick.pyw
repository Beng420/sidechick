from pathlib import Path

try:
    import webview
except ImportError as exc:
    raise SystemExit(
        "Missing package: pywebview\n"
        "Install it with:\n"
        "  python -m pip install -r requirements.txt"
    ) from exc

from backend.api import SidechickAPI
from backend.config import APP_VERSION


APP_DIR = Path(__file__).resolve().parent
UI_PATH = APP_DIR / "ui" / "index.html"


def main():
    api = SidechickAPI()
    window = webview.create_window(
        f"Sidechick {APP_VERSION}",
        UI_PATH.as_uri(),
        js_api=api,
        width=1120,
        height=760,
        min_size=(900, 620),
    )
    webview.start(debug=False)
    api.shutdown()


if __name__ == "__main__":
    main()
