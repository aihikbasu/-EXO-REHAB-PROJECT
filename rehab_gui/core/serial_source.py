import time

try:
    import serial
except ImportError:
    serial = None


class SerialSensorSource:
    """Real hardware version of SensorSource -- same interface, talks over
    a serial link instead of generating numbers. Swap this in for
    SensorSource once a device is available; the GUI pages don't need to
    change since both classes expose the same methods.

    Assumed wire format (adjust once firmware is confirmed):
      - Outgoing commands: "<controller/state/stance/swing/estim>\n"
      - Ack: a single line "OK\n" (or "ERR\n" on failure)
      - Streamed samples: "angle,torque,current,pot_raw\n"
    """

    def __init__(self):
        self._conn = None
        self.connected = False
        self.calibrating = False
        self.cal_min = None
        self.cal_max = None

    def connect(self, port="COM3", baud=115200, timeout=1.0):
        if serial is None:
            raise RuntimeError("pyserial is not installed -- pip install pyserial")
        self._conn = serial.Serial(port, baudrate=baud, timeout=timeout)
        time.sleep(2)  # most boards reset on serial open, give it a moment
        self.connected = True

    def disconnect(self):
        if self._conn is not None:
            self._conn.close()
        self.connected = False

    def start_calibration(self):
        self.calibrating = True
        self.cal_min = None
        self.cal_max = None

    def stop_calibration(self):
        self.calibrating = False

    def read(self):
        if not self.connected:
            raise RuntimeError("not connected")

        line = self._conn.readline().decode("utf-8", errors="ignore").strip()
        parts = line.split(",")
        if len(parts) != 4:
            return {"angle": 0.0, "torque": 0.0, "current": 0.0, "pot_raw": 0.0}

        angle, torque, current, pot_raw = (float(p) for p in parts)

        if self.calibrating:
            if self.cal_min is None or pot_raw < self.cal_min:
                self.cal_min = pot_raw
            if self.cal_max is None or pot_raw > self.cal_max:
                self.cal_max = pot_raw

        return {"angle": angle, "torque": torque, "current": current, "pot_raw": pot_raw}

    def build_settings_string(self, controller, state, stance, swing, estim):
        return f"<{controller}/{state}/{stance}/{swing}/{estim}>"

    def upload_settings(self, settings_str):
        if not self.connected:
            raise RuntimeError("not connected")
        self._conn.write((settings_str + "\n").encode("utf-8"))
        ack = self._conn.readline().decode("utf-8", errors="ignore").strip()
        return ack == "OK"

    def run_diagnostic(self, kind, on_progress):
        """Sends a diagnostic command and expects a line per progress tick,
        finishing with 'PASS,<metric>' or 'FAIL,<metric>'. Adjust the
        command/response format to match firmware once available."""
        if not self.connected:
            raise RuntimeError("not connected")

        self._conn.write(f"<diag/{kind}>\n".encode("utf-8"))
        metric = 0.0
        while True:
            line = self._conn.readline().decode("utf-8", errors="ignore").strip()
            if line.startswith("PROGRESS,"):
                frac = float(line.split(",")[1])
                on_progress(frac)
            elif line.startswith("PASS,"):
                metric = float(line.split(",")[1])
                return True, metric
            elif line.startswith("FAIL,"):
                metric = float(line.split(",")[1])
                return False, metric
            elif line == "":
                return False, metric  # timed out
