import customtkinter as ctk
from src import config
import tkinter as tk

def create_labeled_widget(p, label_text, char_width, widget_type="entry", widget_params=None):
    frame = ctk.CTkFrame(p, fg_color="transparent")
    ctk.CTkLabel(frame, text=f"{label_text}:").pack(side="left", padx=(0, 3), pady=5)
    pixel_width = char_width * 9
    if pixel_width < 80 and widget_type in ["combo", "dropbox"]:
        pixel_width = 80
    
    widget_params = widget_params or {}
    if 'fg_color' not in widget_params:
        widget_params['fg_color'] = config.COLOR_THEME["widget"]
    if 'text_color' not in widget_params:
        widget_params['text_color'] = config.COLOR_THEME["text"]

    widget = None
    if widget_type.lower() in ["combo", "dropbox"]:
        widget = ctk.CTkComboBox(frame, width=pixel_width, **widget_params)
    elif widget_type.lower() == "checkbox":
        widget = ctk.CTkCheckBox(frame, text="", **widget_params)
    else:
        widget = ctk.CTkEntry(frame, width=pixel_width, **widget_params)
    
    widget.pack(side="left", pady=5)
    frame.pack(side="left", padx=(0,10))
    return frame, widget