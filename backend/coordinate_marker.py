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
        self.virtual_left = 0
        self.virtual_top = 0
        self.virtual_width = 1
        self.virtual_height = 1

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
        monitor = command.get("monitor") or {}
        self.virtual_left = int(monitor.get("left", 0))
        self.virtual_top = int(monitor.get("top", 0))
        self.virtual_width = int(monitor.get("width", 1))
        self.virtual_height = int(monitor.get("height", 1))

        geometry = (
            f"{self.virtual_width}x{self.virtual_height}"
            f"{self.virtual_left:+d}{self.virtual_top:+d}"
        )
        self.root.geometry(geometry)
        self.canvas.config(width=self.virtual_width, height=self.virtual_height)
        self.root.deiconify()
        self.root.lift()

        x = int(command["x"]) - self.virtual_left
        y = int(command["y"]) - self.virtual_top
        radius = int(command.get("radius", 30))
        self.draw_marker(x, y, radius, int(command["x"]), int(command["y"]))

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
        label_x = min(max(x + r + 18, 10), max(10, self.virtual_width - 250))
        label_y = min(max(y - r - 10, 10), max(10, self.virtual_height - 44))
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


if __name__ == "__main__":
    enable_dpi_awareness()
    MarkerApp().run()
