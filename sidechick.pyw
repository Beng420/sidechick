from pathlib import Path
import subprocess
import sys


APP_DIR = Path(__file__).resolve().parent
UI_PATH = APP_DIR / "ui" / "index.html"
REQUIREMENTS_PATH = APP_DIR / "requirements.txt"


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


def import_webview():
    try:
        import webview
    except ImportError as exc:
        return None, exc
    return webview, None


def install_requirements():
    if not REQUIREMENTS_PATH.exists():
        return False, "requirements.txt was not found."

    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", str(REQUIREMENTS_PATH)],
        cwd=str(APP_DIR),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return result.returncode == 0, result.stdout


def show_dependency_prompt(missing_package: str) -> bool:
    try:
        import tkinter as tk
        from tkinter import messagebox
    except ImportError:
        raise SystemExit(
            f"Missing package: {missing_package}\n"
            "Install it with:\n"
            f"  {sys.executable} -m pip install -r requirements.txt"
        )

    installed = False
    root = tk.Tk()
    root.title("Sidechick dependencies")
    root.geometry("440x220")
    root.resizable(False, False)

    message = (
        "To open Sidechick, dependencies need to be installed first.\n\n"
        f"Missing right now: {missing_package}"
    )
    tk.Label(root, text=message, padx=22, pady=18, justify="left", wraplength=390).pack(anchor="w")
    status = tk.StringVar(value="")
    tk.Label(root, textvariable=status, padx=22, justify="left", wraplength=390).pack(anchor="w")

    buttons = tk.Frame(root, padx=22, pady=18)
    buttons.pack(side="bottom", fill="x")

    def do_install():
        nonlocal installed
        install_button.config(state="disabled")
        close_button.config(state="disabled")
        status.set("Installing dependencies...")
        root.update_idletasks()

        ok, output = install_requirements()
        if ok:
            installed = True
            messagebox.showinfo("Sidechick", "Dependencies installed. Sidechick will open now.")
            root.destroy()
            return

        close_button.config(state="normal")
        install_button.config(state="normal")
        status.set("Install failed.")
        messagebox.showerror("Sidechick", str(output)[-2500:])

    install_button = tk.Button(buttons, text="Install dependencies", command=do_install)
    install_button.pack(side="left")
    close_button = tk.Button(buttons, text="Close", command=root.destroy)
    close_button.pack(side="right")

    root.mainloop()
    return installed


def main():
    enable_dpi_awareness()

    webview, import_error = import_webview()
    if webview is None:
        missing_package = import_error.name or "pywebview"
        if not show_dependency_prompt(missing_package):
            raise SystemExit(1)
        webview, import_error = import_webview()
        if webview is None:
            raise SystemExit(f"Missing package after install: {import_error.name or 'pywebview'}")

    from backend.api import SidechickAPI
    from backend.config import APP_VERSION

    api = SidechickAPI()
    window = webview.create_window(
        f"Sidechick {APP_VERSION}",
        UI_PATH.as_uri(),
        js_api=api,
        width=1280,
        height=820,
        min_size=(1040, 680),
    )
    webview.start(debug=False)
    api.shutdown()


if __name__ == "__main__":
    main()
