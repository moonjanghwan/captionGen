import customtkinter as ctk
from src import config
import tkinter as tk
from tkinter import ttk

class TextSettingsTab(ctk.CTkFrame):
    def __init__(self, parent, default_data):
        super().__init__(parent, fg_color=config.COLOR_THEME["widget"])
        # ... (rest of the file, assuming it's similar to the one in image_tab_view)
        self.defaults = {
            "conversation": {"행수": "4", "비율": "16:9", "해상도": "1920x1080", "rows": []},
            "thumbnail": {"행수": "4", "비율": "16:9", "해상도": "1920x1080", "rows": []},
            "intro": {"행수": "1", "비율": "16:9", "해상도": "1920x1080", "rows": []},
            "ending": {"행수": "1", "비율": "16:9", "해상도": "1920x1080", "rows": []},
            "dialogue": {"행수": "3", "비율": "16:9", "해상도": "1920x1080", "rows": []},
        }
        # ...
        for name in ["conversation", "thumbnail", "intro", "ending", "dialogue"]:
            # ...
            pass