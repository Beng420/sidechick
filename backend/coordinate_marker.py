import json
import queue
import sys
import threading
import tkinter as tk


BACKGROUND = "#000001"
ACCENT = "#d8ff5f"
DANGER = "#3db7ff"
PANEL = "#101215"
TEXT = "#f2f0eb"
HWND_TOPMOST = -1
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
MONITOR_DEFAULTTONEAREST = 2


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


class MarkerApp:
    def __init__(self):
        self.commands = queue.Queue()
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        try:
            self.root.attributes("-toolwindow", True)
        except tk.TclError:
            pass
        try:
            self.root.attributes("-transparentcolor", BACKGROUND)
        except tk.TclError:
            self.root.attributes("-alpha", 0.92)
        try:
            self.root.attributes("-disabled", True)
        except tk.TclError:
            pass

        self.canvas = tk.Canvas(self.root, bg=BACKGROUND, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.monitor_left = 0
        self.monitor_top = 0
        self.monitor_width = 1
        self.monitor_height = 1

    def run(self):
        threading.Thread(target=self.read_commands, daemon=True).start()
        self.root.after(40, self.process_commands)
        self.root.mainloop()

    def read_commands(self):
        for line in sys.stdin:
            try:
                self.commands.put(json.loads(line))
            except json.JSONDecodeError:
                continue
        self.commands.put({"command": "close"})

    def process_commands(self):
        while True:
            try:
                command = self.commands.get_nowait()
            except queue.Empty:
                break

            name = command.get("command")
            if name == "show":
                self.show_marker(command)
            elif name == "close":
                self.root.destroy()
                return

        self.root.after(40, self.process_commands)

    def show_marker(self, command):
        screen_x = int(command["x"])
        screen_y = int(command["y"])
        monitor = command.get("monitor") or {}
        if sys.platform.startswith("win"):
            monitor = windows_monitor_for_point(screen_x, screen_y) or monitor

        self.monitor_left = int(monitor.get("left", 0))
        self.monitor_top = int(monitor.get("top", 0))
        self.monitor_width = int(monitor.get("width", 1))
        self.monitor_height = int(monitor.get("height", 1))

        self.size_window()
        self.root.deiconify()
        self.root.update_idletasks()
        self.place_window()
        self.root.lift()

        x = screen_x - self.monitor_left
        y = screen_y - self.monitor_top
        radius = int(command.get("radius", 30))
        self.draw_marker(x, y, radius, screen_x, screen_y)
        self.root.after(20, self.place_window)

    def size_window(self):
        width = max(1, self.monitor_width)
        height = max(1, self.monitor_height)
        self.root.geometry(f"{width}x{height}")
        self.canvas.config(width=width, height=height)
        self.root.update_idletasks()

    def place_window(self):
        width = max(1, self.monitor_width)
        height = max(1, self.monitor_height)

        if not sys.platform.startswith("win"):
            self.root.geometry(f"{width}x{height}{self.monitor_left:+d}{self.monitor_top:+d}")
            return

        try:
            import ctypes

            hwnd = self.root.winfo_id()
            ctypes.windll.user32.SetWindowPos(
                hwnd,
                HWND_TOPMOST,
                self.monitor_left,
                self.monitor_top,
                width,
                height,
                SWP_NOACTIVATE | SWP_SHOWWINDOW,
            )
        except Exception:
            self.root.geometry(f"{width}x{height}{self.monitor_left:+d}{self.monitor_top:+d}")

    def draw_marker(self, x, y, radius, screen_x, screen_y):
        self.canvas.delete("all")
        r = radius

        self.canvas.create_oval(x - r, y - r, x + r, y + r, outline=ACCENT, width=2)
        self.canvas.create_line(x - r - 14, y, x - 8, y, fill=DANGER, width=2)
        self.canvas.create_line(x + 8, y, x + r + 14, y, fill=DANGER, width=2)
        self.canvas.create_line(x, y - r - 14, x, y - 8, fill=DANGER, width=2)
        self.canvas.create_line(x, y + 8, x, y + r + 14, fill=DANGER, width=2)
        self.canvas.create_rectangle(x - 3, y - 3, x + 3, y + 3, outline=ACCENT, width=2)

        for offset in range(-r, r + 1, 10):
            if abs(offset) < 8:
                continue
            self.canvas.create_line(x + offset, y - r, x + offset, y + r, fill=ACCENT, width=1)
            self.canvas.create_line(x - r, y + offset, x + r, y + offset, fill=ACCENT, width=1)

        label = f"Position {screen_x}, {screen_y} markiert"
        label_x = min(max(x + r + 18, 10), max(10, self.monitor_width - 250))
        label_y = min(max(y - r - 10, 10), max(10, self.monitor_height - 44))
        text_id = self.canvas.create_text(
            label_x + 10,
            label_y + 8,
            text=label,
            anchor="nw",
            fill=TEXT,
            font=("Segoe UI", 11, "bold"),
        )
        bounds = self.canvas.bbox(text_id)
        if bounds:
            box = self.canvas.create_rectangle(
                bounds[0] - 8,
                bounds[1] - 5,
                bounds[2] + 8,
                bounds[3] + 5,
                fill=PANEL,
                outline=ACCENT,
                width=1,
            )
            self.canvas.tag_lower(box, text_id)


def windows_monitor_for_point(x, y):
    try:
        import ctypes
        from ctypes import wintypes

        class POINT(ctypes.Structure):
            _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

        class RECT(ctypes.Structure):
            _fields_ = [
                ("left", wintypes.LONG),
                ("top", wintypes.LONG),
                ("right", wintypes.LONG),
                ("bottom", wintypes.LONG),
            ]

        class MONITORINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.DWORD),
                ("rcMonitor", RECT),
                ("rcWork", RECT),
                ("dwFlags", wintypes.DWORD),
            ]

        point = POINT(int(x), int(y))
        handle = ctypes.windll.user32.MonitorFromPoint(point, MONITOR_DEFAULTTONEAREST)
        if not handle:
            return None

        info = MONITORINFO()
        info.cbSize = ctypes.sizeof(MONITORINFO)
        if not ctypes.windll.user32.GetMonitorInfoW(handle, ctypes.byref(info)):
            return None

        rect = info.rcMonitor
        return {
            "left": int(rect.left),
            "top": int(rect.top),
            "width": int(rect.right - rect.left),
            "height": int(rect.bottom - rect.top),
        }
    except Exception:
        return None


if __name__ == "__main__":
    enable_dpi_awareness()
    MarkerApp().run()
