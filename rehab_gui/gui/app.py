import tkinter as tk

from core.config_store import load_config, save_config
from core.sensor_source import SensorSource
from gui.nav import NavBar
from gui.pages.instructions import InstructionsPage
from gui.pages.preliminary_testing import PreliminaryTestingPage
from gui.pages.run_trial import RunTrialPage

PAGES = [
    ("instructions", "Instructions"),
    ("preliminary", "Preliminary Testing"),
    ("trial", "Run Trial"),
]


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Exoskeleton GUI")
        self.geometry("1180x760")
        self.configure(bg="white")

        self.config = load_config()
        self.sensor = SensorSource()
        self.sensor.cal_min = self.config["calibration"]["min"]
        self.sensor.cal_max = self.config["calibration"]["max"]

        self.nav = NavBar(self, PAGES, self.show_page)
        self.nav.pack(side="top", fill="x")

        self.body = tk.Frame(self, bg="white")
        self.body.pack(side="top", fill="both", expand=True)

        self.status = tk.Label(
            self, text="Simulated data -- no device connected", bg="#fef3c7",
            fg="#92400e", anchor="w", padx=12, pady=4, font=("Segoe UI", 9),
        )
        self.status.pack(side="bottom", fill="x")

        self.pages = {}
        self._current = None
        self._build_pages()
        self.show_page("instructions")

    def _build_pages(self):
        self.pages["instructions"] = InstructionsPage(
            self.body, self.sensor, self.set_status, self.config, self.save_config
        )
        self.pages["preliminary"] = PreliminaryTestingPage(
            self.body, self.sensor, self.set_status, self.config, self.save_config
        )
        self.pages["trial"] = RunTrialPage(
            self.body, self.sensor, self.set_status, self.config, self.save_config
        )

    def save_config(self):
        save_config(self.config)

    def show_page(self, key):
        if self._current is not None:
            self.pages[self._current].pack_forget()
        self.pages[key].pack(fill="both", expand=True)
        self._current = key
        self.nav.set_active(key)

    def set_status(self, text, connected):
        self.status.configure(
            text=f"{text} -- {'device connected' if connected else 'no device connected'}",
            bg="#dcfce7" if connected else "#fef3c7",
            fg="#166534" if connected else "#92400e",
        )
