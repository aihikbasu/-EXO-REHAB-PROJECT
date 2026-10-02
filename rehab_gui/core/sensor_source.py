import math
import random
import time


class SensorSource:
    """Stand-in for the serial/Bluetooth link to the exoskeleton.

    Generates plausible joint angle, torque, and motor current values so the
    GUI can be built and demoed before hardware is available. Swap this out
    for a real reader once the microcontroller side is ready -- the page
    code only ever calls read() and doesn't care where the numbers come from.
    """

    def __init__(self):
        self._t0 = time.time()
        self.connected = False
        self.calibrating = False
        self.cal_min = None
        self.cal_max = None

    def connect(self):
        self.connected = True

    def disconnect(self):
        self.connected = False

    def start_calibration(self):
        self.calibrating = True
        self.cal_min = None
        self.cal_max = None

    def stop_calibration(self):
        self.calibrating = False

    def read(self):
        t = time.time() - self._t0
        angle = 35 * math.sin(t * 0.9) + random.uniform(-1.5, 1.5)
        torque = 4 * math.sin(t * 0.9 + 0.4) + random.uniform(-0.3, 0.3)
        current = 0.8 + 0.3 * math.sin(t * 1.8) + random.uniform(-0.05, 0.05)
        pot_raw = 512 + 400 * math.sin(t * 0.9) + random.uniform(-4, 4)

        if self.calibrating:
            if self.cal_min is None or pot_raw < self.cal_min:
                self.cal_min = pot_raw
            if self.cal_max is None or pot_raw > self.cal_max:
                self.cal_max = pot_raw

        return {
            "angle": angle,
            "torque": torque,
            "current": current,
            "pot_raw": pot_raw,
        }

    def build_settings_string(self, controller, state, stance, swing, estim):
        """Pack Run Trial settings into the device's delimited command format."""
        return f"<{controller}/{state}/{stance}/{swing}/{estim}>"

    def upload_settings(self, settings_str):
        """Simulated handshake -- real hardware would echo an ack byte back."""
        time.sleep(0.4)
        return True

    def run_diagnostic(self, kind, on_progress):
        """Blocking simulated sweep -- call from a worker thread.

        on_progress(fraction) is called repeatedly with 0..1. Returns
        (passed, metric) once the sweep finishes.
        """
        steps = 30
        for i in range(steps):
            time.sleep(0.05)
            on_progress((i + 1) / steps)

        if kind == "torque":
            metric = random.uniform(0.02, 0.18)
            passed = metric < 0.12
        elif kind == "impedance":
            metric = random.uniform(0.5, 4.0)
            passed = metric < 2.5
        else:  # speed
            metric = random.uniform(0.05, 0.4)
            passed = metric < 0.25

        return passed, metric
