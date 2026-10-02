import tkinter as tk

TEAL = "#0f766e"
TEAL_LIGHT = "#ccfbf1"
GREY = "#6b7280"
BG = "#1f2937"


class NavBar(tk.Frame):
    def __init__(self, master, pages, on_select, **kwargs):
        super().__init__(master, bg=BG, height=52, **kwargs)
        self.pack_propagate(False)

        self._buttons = {}
        self._active = None

        title = tk.Label(
            self, text="Exoskeleton GUI", bg=BG, fg="white",
            font=("Segoe UI", 12, "bold"), padx=16,
        )
        title.pack(side="left")

        for key, label in pages:
            btn = tk.Label(
                self, text=label, bg=BG, fg=GREY,
                font=("Segoe UI", 10, "bold"), padx=14, pady=16, cursor="hand2",
            )
            btn.bind("<Button-1>", lambda e, k=key: on_select(k))
            btn.pack(side="left")
            self._buttons[key] = btn

    def set_active(self, key):
        for k, btn in self._buttons.items():
            if k == key:
                btn.configure(fg=TEAL, bg=TEAL_LIGHT)
            else:
                btn.configure(fg=GREY, bg=BG)
        self._active = key
