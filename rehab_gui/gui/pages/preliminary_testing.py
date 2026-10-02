import threading
import tkinter as tk
from collections import deque
from tkinter import ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

HISTORY_LEN = 150


class PreliminaryTestingPage(tk.Frame):
    def __init__(self, master, sensor, set_status, config, save_config, **kwargs):
        super().__init__(master, bg="white", **kwargs)
        self.sensor = sensor
        self.set_status = set_status
        self.config = config
        self.save_config = save_config

        self.angle_hist = deque(maxlen=HISTORY_LEN)
        self.torque_hist = deque(maxlen=HISTORY_LEN)
        self.current_hist = deque(maxlen=HISTORY_LEN)

        self._build_layout()
        self._streaming = True
        self.after(33, self._tick)  # ~30 Hz

    def _build_layout(self):
        left = tk.Frame(self, bg="white")
        left.pack(side="left", fill="both", expand=True, padx=(16, 8), pady=16)

        right = tk.Frame(self, bg="white", width=340)
        right.pack(side="right", fill="y", padx=(8, 16), pady=16)
        right.pack_propagate(False)

        self._build_plots(left)
        self._build_calibration(right)
        self._build_diagnostics(right)

    def _build_plots(self, parent):
        self.fig = Figure(figsize=(6, 5), dpi=100)
        self.ax_angle = self.fig.add_subplot(211)
        self.ax_torque = self.fig.add_subplot(212)

        self.ax_angle.set_title("Joint angle (deg)")
        self.ax_torque.set_title("Torque (Nm) / Motor current (A)")

        (self.line_angle,) = self.ax_angle.plot([], [], color="#0f766e")
        (self.line_torque,) = self.ax_torque.plot([], [], color="#2563eb", label="torque")
        (self.line_current,) = self.ax_torque.plot([], [], color="#dc2626", label="current")
        self.ax_torque.legend(loc="upper right", fontsize=8)

        self.fig.tight_layout()

        self.canvas = FigureCanvasTkAgg(self.fig, master=parent)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def _build_calibration(self, parent):
        box = tk.LabelFrame(parent, text="Potentiometer Calibration", bg="white", padx=10, pady=10)
        box.pack(fill="x", pady=(0, 12))

        self.pot_var = tk.StringVar(value="raw: --")
        tk.Label(box, textvariable=self.pot_var, bg="white", font=("Segoe UI", 10)).pack(anchor="w")

        cal = self.config["calibration"]
        initial_range = (
            f"min/max: {cal['min']:.0f} / {cal['max']:.0f}"
            if cal["min"] is not None else "min/max: --"
        )
        self.range_var = tk.StringVar(value=initial_range)
        tk.Label(box, textvariable=self.range_var, bg="white", font=("Segoe UI", 10)).pack(anchor="w", pady=(2, 8))

        self.cal_btn = ttk.Button(box, text="Start Calibration", command=self._toggle_cal)
        self.cal_btn.pack(fill="x")

    def _toggle_cal(self):
        if self.sensor.calibrating:
            self.sensor.stop_calibration()
            self.cal_btn.configure(text="Start Calibration")
            self.config["calibration"]["min"] = self.sensor.cal_min
            self.config["calibration"]["max"] = self.sensor.cal_max
            self.save_config()
        else:
            self.sensor.start_calibration()
            self.cal_btn.configure(text="Stop && Lock In")

    def _build_diagnostics(self, parent):
        box = tk.LabelFrame(parent, text="Diagnostic Tests", bg="white", padx=10, pady=10)
        box.pack(fill="x")

        self.diag_widgets = {}
        for kind, label in (("torque", "Torque"), ("impedance", "Impedance"), ("speed", "Speed")):
            row = tk.Frame(box, bg="white")
            row.pack(fill="x", pady=6)

            btn = ttk.Button(row, text=label, width=10, command=lambda k=kind: self._run_diag(k))
            btn.pack(side="left")

            bar = ttk.Progressbar(row, length=120, mode="determinate")
            bar.pack(side="left", padx=8)

            result = tk.Label(row, text="", bg="white", width=14, anchor="w")
            result.pack(side="left")

            self.diag_widgets[kind] = (btn, bar, result)

    def _run_diag(self, kind):
        btn, bar, result = self.diag_widgets[kind]
        btn.configure(state="disabled")
        result.configure(text="running...", fg="#6b7280")
        bar["value"] = 0

        def progress(frac):
            self.after(0, lambda: bar.configure(value=frac * 100))

        def worker():
            passed, metric = self.sensor.run_diagnostic(kind, progress)
            self.after(0, lambda: self._diag_done(kind, passed, metric))

        threading.Thread(target=worker, daemon=True).start()

    def _diag_done(self, kind, passed, metric):
        btn, bar, result = self.diag_widgets[kind]
        btn.configure(state="normal")
        if passed:
            result.configure(text=f"PASS ({metric:.2f})", fg="#16a34a")
        else:
            result.configure(text=f"FAIL ({metric:.2f})", fg="#dc2626")

    def _tick(self):
        sample = self.sensor.read()
        self.angle_hist.append(sample["angle"])
        self.torque_hist.append(sample["torque"])
        self.current_hist.append(sample["current"])

        xs = range(len(self.angle_hist))
        self.line_angle.set_data(xs, self.angle_hist)
        self.ax_angle.relim()
        self.ax_angle.autoscale_view()

        self.line_torque.set_data(xs, self.torque_hist)
        self.line_current.set_data(xs, self.current_hist)
        self.ax_torque.relim()
        self.ax_torque.autoscale_view()

        self.canvas.draw_idle()

        self.pot_var.set(f"raw: {sample['pot_raw']:.0f}")
        if self.sensor.cal_min is not None:
            self.range_var.set(f"min/max: {self.sensor.cal_min:.0f} / {self.sensor.cal_max:.0f}")

        status = "Simulated data" if not self.sensor.connected else "Device connected"
        self.set_status(status, connected=self.sensor.connected)

        if self._streaming:
            self.after(33, self._tick)

    def stop(self):
        self._streaming = False
