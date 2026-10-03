import threading
import time
import tkinter as tk
from tkinter import ttk

from core.emg_control import EMGProportionalController

CONTROLLERS = [
    ("0", "Zero Torque"),
    ("1", "Assist-as-Needed"),
    ("2", "Trajectory Tracking"),
    ("3", "Impedance Control"),
]


class RunTrialPage(tk.Frame):
    def __init__(self, master, sensor, set_status, config, save_config, **kwargs):
        super().__init__(master, bg="white", **kwargs)
        self.sensor = sensor
        self.set_status = set_status
        self.config = config
        self.save_config = save_config

        trial = self.config["trial"]
        self.controller_var = tk.StringVar(value=trial["controller"])
        self.stance_var = tk.StringVar(value=trial["stance"])
        self.swing_var = tk.StringVar(value=trial["swing"])
        self.estim_var = tk.BooleanVar(value=trial["estim"])

        self.logging_active = False
        self.log_start_time = None
        self.log_rows = 0

        tk.Label(
            self, text="Run Trial", bg="white",
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor="w", padx=24, pady=(24, 4))

        self.emg_controller = EMGProportionalController()

        self._build_strategy_panel()
        self._build_emg_panel()
        self._build_logging_panel()

    def _build_strategy_panel(self):
        panel = tk.LabelFrame(self, text="Assistance Strategy", bg="white", padx=16, pady=16)
        panel.pack(anchor="w", padx=24, fill="x", pady=(8, 12))

        row = tk.Frame(panel, bg="white")
        row.pack(anchor="w", fill="x", pady=4)
        tk.Label(row, text="Controller", bg="white", width=14, anchor="w").pack(side="left")
        combo = ttk.Combobox(
            row, state="readonly", width=22,
            values=[label for _, label in CONTROLLERS],
        )
        start_index = next(
            (i for i, (cid, _) in enumerate(CONTROLLERS) if cid == self.controller_var.get()), 0
        )
        combo.current(start_index)
        combo.bind("<<ComboboxSelected>>", lambda e: self._set_controller(combo.current()))
        combo.pack(side="left")

        self._setpoint_row(panel, "Stance setpoint", self.stance_var)
        self._setpoint_row(panel, "Swing setpoint", self.swing_var)

        estim_row = tk.Frame(panel, bg="white")
        estim_row.pack(anchor="w", pady=(8, 12))
        ttk.Checkbutton(
            estim_row, text="Enable e-stim channel", variable=self.estim_var,
        ).pack(anchor="w")

        self.preview_var = tk.StringVar(value="")
        tk.Label(
            panel, textvariable=self.preview_var, bg="white", fg="#6b7280",
            font=("Consolas", 9),
        ).pack(anchor="w", pady=(0, 8))

        self.upload_btn = ttk.Button(panel, text="Upload Settings", command=self._upload)
        self.upload_btn.pack(anchor="w")

        self._update_preview()

    def _setpoint_row(self, parent, label, var):
        row = tk.Frame(parent, bg="white")
        row.pack(anchor="w", fill="x", pady=4)
        tk.Label(row, text=label, bg="white", width=14, anchor="w").pack(side="left")
        ttk.Entry(row, textvariable=var, width=8).pack(side="left")

    def _set_controller(self, index):
        self.controller_var.set(CONTROLLERS[index][0])
        self._update_preview()

    def _update_preview(self):
        settings = self.sensor.build_settings_string(
            self.controller_var.get(), "1",
            self.stance_var.get(), self.swing_var.get(),
            "1" if self.estim_var.get() else "0",
        )
        self.preview_var.set(f"command: {settings}")

    def _upload(self):
        self._update_preview()
        self.upload_btn.configure(state="disabled", text="Uploading...")
        settings = self.sensor.build_settings_string(
            self.controller_var.get(), "1",
            self.stance_var.get(), self.swing_var.get(),
            "1" if self.estim_var.get() else "0",
        )

        def worker():
            ok = self.sensor.upload_settings(settings)
            self.after(0, lambda: self._upload_done(ok))

        threading.Thread(target=worker, daemon=True).start()

    def _upload_done(self, ok):
        self.upload_btn.configure(state="normal", text="Upload Settings")
        self.set_status("Settings uploaded" if ok else "Upload failed", connected=self.sensor.connected)

        if ok:
            trial = self.config["trial"]
            trial["controller"] = self.controller_var.get()
            trial["stance"] = self.stance_var.get()
            trial["swing"] = self.swing_var.get()
            trial["estim"] = self.estim_var.get()
            self.save_config()

    def _build_emg_panel(self):
        panel = tk.LabelFrame(
            self, text="EMG Confidence-Weighted Control (trained classifier)",
            bg="white", padx=16, pady=16,
        )
        panel.pack(anchor="w", padx=24, fill="x", pady=(0, 12))

        if not self.emg_controller.available:
            tk.Label(
                panel, bg="white", fg="#b91c1c",
                text=f"Classifier model not available: {self.emg_controller.load_error}",
                wraplength=500, justify="left",
            ).pack(anchor="w")
            return

        tk.Label(
            panel, bg="white", fg="#6b7280", wraplength=520, justify="left",
            text=(
                "Instead of switching strategies on a single hard prediction, this blends "
                "stance/swing setpoints proportionally to the classifier's confidence across "
                "all four gestures. Each sample below is a real feature row from the trained "
                "model's held-out test set, not a fabricated number."
            ),
        ).pack(anchor="w", pady=(0, 10))

        self.emg_bars = {}
        for gesture in ("rest", "flexion", "extension", "grasp"):
            row = tk.Frame(panel, bg="white")
            row.pack(anchor="w", fill="x", pady=2)
            tk.Label(row, text=gesture, bg="white", width=12, anchor="w").pack(side="left")
            bar = ttk.Progressbar(row, length=200, mode="determinate", maximum=100)
            bar.pack(side="left", padx=(0, 8))
            pct = tk.Label(row, text="0%", bg="white", width=6)
            pct.pack(side="left")
            self.emg_bars[gesture] = (bar, pct)

        self.emg_blend_var = tk.StringVar(value="Blended setpoint: --")
        tk.Label(
            panel, textvariable=self.emg_blend_var, bg="white",
            font=("Consolas", 9), fg="#0f766e",
        ).pack(anchor="w", pady=(8, 10))

        self.emg_sample_btn = ttk.Button(
            panel, text="Sample EMG Window", command=self._sample_emg,
        )
        self.emg_sample_btn.pack(anchor="w")

        self.emg_apply_btn = ttk.Button(
            panel, text="Apply Blended Setpoint to Controls Above",
            command=self._apply_emg_blend, state="disabled",
        )
        self.emg_apply_btn.pack(anchor="w", pady=(6, 0))

        self._last_blend = None

    def _sample_emg(self):
        features, true_label = self.emg_controller.sample_window()
        result = self.emg_controller.predict_proportional(features)

        for gesture, (bar, pct) in self.emg_bars.items():
            p = result["probabilities"].get(gesture, 0.0) * 100
            bar["value"] = p
            pct.configure(text=f"{p:.0f}%")

        self.emg_blend_var.set(
            f"Blended setpoint: stance={result['blended_stance']}, "
            f"swing={result['blended_swing']}  (true label: {true_label})"
        )
        self._last_blend = result
        self.emg_apply_btn.configure(state="normal")

    def _apply_emg_blend(self):
        if self._last_blend is None:
            return
        self.stance_var.set(str(self._last_blend["blended_stance"]))
        self.swing_var.set(str(self._last_blend["blended_swing"]))
        self._update_preview()

    def _build_logging_panel(self):
        panel = tk.LabelFrame(self, text="Data Logging", bg="white", padx=16, pady=16)
        panel.pack(anchor="w", padx=24, fill="x")

        self.log_status_var = tk.StringVar(value="Not logging")
        tk.Label(panel, textvariable=self.log_status_var, bg="white", font=("Segoe UI", 10)).pack(anchor="w")

        self.log_btn = ttk.Button(panel, text="Start Logging", command=self._toggle_logging)
        self.log_btn.pack(anchor="w", pady=(8, 0))

    def _toggle_logging(self):
        if self.logging_active:
            self.logging_active = False
            self.log_btn.configure(text="Start Logging")
            elapsed = time.time() - self.log_start_time
            self.log_status_var.set(f"Stopped -- {self.log_rows} rows over {elapsed:.1f}s")
        else:
            self.logging_active = True
            self.log_start_time = time.time()
            self.log_rows = 0
            self.log_btn.configure(text="Stop Logging")
            self._log_tick()

    def _log_tick(self):
        if not self.logging_active:
            return
        sample = self.sensor.read()
        self.log_rows += 1
        elapsed = time.time() - self.log_start_time
        self.log_status_var.set(f"Logging -- {self.log_rows} rows, {elapsed:.1f}s elapsed")
        self.after(33, self._log_tick)
