import tkinter as tk
from tkinter import ttk

try:
    import serial
except ImportError:
    serial = None

GUIDELINES = (
    "Before running a trial, confirm the device is powered on and the "
    "emergency-stop switch is within reach of the operator.\n\n"
    "Choose a connection mode below, then fill in the fields for that mode. "
    "Only the settings relevant to your choice are enabled -- the rest stay "
    "greyed out to keep setup simple.\n\n"
    "Once connected, move to Preliminary Testing before starting any trial."
)


class InstructionsPage(tk.Frame):
    def __init__(self, master, sensor, set_status, config, save_config, **kwargs):
        super().__init__(master, bg="white", **kwargs)
        self.sensor = sensor
        self.set_status = set_status
        self.config = config
        self.save_config = save_config

        conn = self.config["connection"]
        self.mode = tk.StringVar(value=conn["mode"])
        self.trigger_var = tk.BooleanVar(value=conn["trigger_enabled"])

        tk.Label(
            self, text="Instructions", bg="white",
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor="w", padx=24, pady=(24, 4))

        tk.Label(
            self, text=GUIDELINES, bg="white", fg="#374151",
            font=("Segoe UI", 10), justify="left", wraplength=560,
        ).pack(anchor="w", padx=24, pady=(0, 16))

        self._build_connection_panel()

    def _build_connection_panel(self):
        conn = self.config["connection"]
        panel = tk.LabelFrame(self, text="Connection Setup", bg="white", padx=16, pady=16)
        panel.pack(anchor="w", padx=24, fill="x")

        mode_row = tk.Frame(panel, bg="white")
        mode_row.pack(anchor="w", pady=(0, 12))

        ttk.Radiobutton(
            mode_row, text="Wired (USB)", variable=self.mode, value="usb",
            command=self._refresh_fields,
        ).pack(side="left", padx=(0, 16))
        ttk.Radiobutton(
            mode_row, text="Wireless (Bluetooth)", variable=self.mode, value="bluetooth",
            command=self._refresh_fields,
        ).pack(side="left")

        self.usb_frame = tk.Frame(panel, bg="white")
        self.usb_frame.pack(anchor="w", fill="x")
        self.com_row = self._labeled_entry(self.usb_frame, "COM Port", conn["com_port"])
        self.baud_row = self._labeled_entry(self.usb_frame, "Baud Rate", conn["baud_rate"])

        self.bt_frame = tk.Frame(panel, bg="white")
        self.bt_frame.pack(anchor="w", fill="x")
        self.device_row = self._labeled_entry(self.bt_frame, "Device Name", conn["device_name"])
        self.pin_row = self._labeled_entry(self.bt_frame, "Pairing PIN", conn["pairing_pin"])

        ttk.Checkbutton(
            panel, text="Enable external trigger pulse (lab-system sync)",
            variable=self.trigger_var,
        ).pack(anchor="w", pady=(8, 12))

        self.use_hardware_var = tk.BooleanVar(value=False)
        hw_check = ttk.Checkbutton(
            panel, text="Use real hardware (requires pyserial + a connected device)",
            variable=self.use_hardware_var,
        )
        hw_check.pack(anchor="w", pady=(0, 12))
        if serial is None:
            hw_check.configure(state="disabled")

        self.connect_btn = ttk.Button(panel, text="Connect", command=self._connect)
        self.connect_btn.pack(anchor="w")

        self._refresh_fields()

    def _labeled_entry(self, parent, label, value):
        row = tk.Frame(parent, bg="white")
        row.pack(anchor="w", fill="x", pady=4)
        tk.Label(row, text=label, bg="white", width=12, anchor="w").pack(side="left")
        entry = ttk.Entry(row, width=20)
        entry.insert(0, value)
        entry.pack(side="left")
        row.entry = entry
        return row

    def _refresh_fields(self):
        usb_state = "normal" if self.mode.get() == "usb" else "disabled"
        bt_state = "normal" if self.mode.get() == "bluetooth" else "disabled"

        for row in self.usb_frame.winfo_children():
            row.entry.configure(state=usb_state)
        for row in self.bt_frame.winfo_children():
            row.entry.configure(state=bt_state)

    def _connect(self):
        if self.use_hardware_var.get():
            self._connect_hardware()
        else:
            self.sensor.connect()
            self.connect_btn.configure(text="Connected", state="disabled")
            self.set_status("Connection established", connected=True)

        conn = self.config["connection"]
        conn["mode"] = self.mode.get()
        conn["com_port"] = self.com_row.entry.get()
        conn["baud_rate"] = self.baud_row.entry.get()
        conn["device_name"] = self.device_row.entry.get()
        conn["pairing_pin"] = self.pin_row.entry.get()
        conn["trigger_enabled"] = self.trigger_var.get()
        self.save_config()

    def _connect_hardware(self):
        from core.serial_source import SerialSensorSource

        port = self.com_row.entry.get()
        baud = int(self.baud_row.entry.get())
        try:
            hw = SerialSensorSource()
            hw.connect(port=port, baud=baud)
            self.connect_btn.configure(text="Hardware connected", state="disabled")
            self.set_status("Hardware connected", connected=True)
        except Exception as exc:
            self.set_status(f"Hardware connect failed: {exc}", connected=False)
