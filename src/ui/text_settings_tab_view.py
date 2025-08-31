import customtkinter as ctk
from src import config
import tkinter as tk

FONTS = ["KoPubWorldDotum", "KoPubWorldBatang", "Noto Sans KR"]

DEFAULTS = {
	"회화 설정": {
		"텍스트 행수": "4",
		"rows": [
			["순번", "50", "50", "1820", "80", FONTS[0], "#FFFFFF", "Bold", "Left", "Top"],
			["원어", "50", "150", "1820", "100", FONTS[0], "#00FFFF", "Bold", "Left", "Top"],
			["학습어", "50", "450", "1820", "100", FONTS[2], "#FF00FF", "Bold", "Left", "Top"],
			["읽기", "50", "750", "1820", "100", FONTS[0], "#FFFF00", "Bold", "Left", "Top"],
		]
	},
	"썸네일 설정": {
		"텍스트 행수": "4",
		"rows": [
			["1행", "50", "50", "924", "100", FONTS[0], "#FFFFFF", "Bold", "Left", "Top"],
			["2행", "50", "200", "924", "100", FONTS[0], "#00FFFF", "Bold", "Left", "Top"],
			["3행", "50", "350", "924", "100", FONTS[0], "#FF00FF", "Bold", "Left", "Top"],
			["4행", "50", "500", "924", "100", FONTS[0], "#FFFF00", "Bold", "Left", "Top"],
		]
	},
	"인트로 설정": {
		"텍스트 행수": "1",
		"rows": [
			["1행", "50", "50", "1820", "100", FONTS[0], "#FFFFFF", "Bold", "Left", "Top"],
		]
	},
	"엔딩 설정": {
		"텍스트 행수": "1",
		"rows": [
			["1행", "50", "50", "1820", "100", FONTS[0], "#FFFFFF", "Bold", "Left", "Top"],
		]
	},
	"대화 설정": {
		"텍스트 행수": "3",
		"rows": [
			["원어", "50", "250", "1820", "100", FONTS[0], "#FFFFFF", "Bold", "Left", "Top"],
			["학습어1", "50", "550", "1820", "100", FONTS[0], "#FFFFFF", "Bold", "Left", "Top"],
			["학습어2", "50", "850", "1820", "100", FONTS[0], "#FFFFFF", "Bold", "Left", "Top"],
		]
	},
}

class TextSettingsTabView(ctk.CTkFrame):
	def __init__(self, parent):
		super().__init__(parent, fg_color=config.COLOR_THEME["background"])
		self.grid_rowconfigure(0, weight=1)
		self.grid_columnconfigure(0, weight=1)
		self._create_widgets()

	def _create_widgets(self):
		self.tabview = ctk.CTkTabview(self, fg_color=config.COLOR_THEME["widget"])
		self.tabview.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
		for name in ["회화 설정", "썸네일 설정", "인트로 설정", "엔딩 설정", "대화 설정"]:
			self.tabview.add(name)
			self._build_form(self.tabview.tab(name), name)

	def _build_form(self, container, tab_name):
		container.grid_columnconfigure(0, weight=1)
		row = ctk.CTkFrame(container, fg_color="transparent")
		row.pack(fill="x", padx=10, pady=(10, 5))
		# 텍스트 행수/화면비율/해상도 (기본값 포함)
		self._add_labeled_combo(row, "텍스트 행수", [str(i) for i in range(1, 11)], default=DEFAULTS[tab_name]["텍스트 행수"], width_chars=6)
		self._add_labeled_combo(row, "화면비율", ["16:9", "9:16", "1:1"], default="16:9", width_chars=10)
		self._add_labeled_combo(row, "해상도", ["1920x1080", "1080x1920", "1080x1080"], default="1920x1080", width_chars=15)

		grid = ctk.CTkFrame(container, fg_color=config.COLOR_THEME["widget"])
		grid.pack(fill="x", padx=10, pady=(5, 10))
		headers = [
			("행", 6), ("x", 6), ("y", 6), ("w", 6), ("크기(pt)", 6), ("폰트(pt)", 30),
			("색상", 10), ("굵기", 8), ("좌우 정렬", 10), ("상하 정렬", 10)
		]
		hdr = ctk.CTkFrame(grid, fg_color="transparent")
		hdr.pack(fill="x", padx=10, pady=(8, 4))
		for label, width in headers:
			lbl = ctk.CTkLabel(hdr, text=label, width=width*9, anchor="center")
			lbl.pack(side="left")

		for values in DEFAULTS[tab_name]["rows"]:
			rowf = ctk.CTkFrame(grid, fg_color="transparent")
			rowf.pack(fill="x", padx=10, pady=2)
			# 행 텍스트
			self._add_entry(rowf, width_chars=6, center=True, default=values[0])
			# x, y, w, 크기(pt)
			self._add_entry(rowf, width_chars=6, center=True, default=values[1])
			self._add_entry(rowf, width_chars=6, center=True, default=values[2])
			self._add_entry(rowf, width_chars=6, center=True, default=values[3])
			self._add_entry(rowf, width_chars=6, center=True, default=values[4])
			# 폰트(pt)
			self._add_combo(rowf, FONTS, width_chars=30, center=True, default=values[5])
			# 색상
			self._add_entry(rowf, width_chars=10, center=True, default=values[6])
			# 굵기
			self._add_combo(rowf, ["Light", "Medium", "Bold"], width_chars=8, center=True, default=values[7])
			# 좌우 정렬
			self._add_combo(rowf, ["Left", "Center", "Right"], width_chars=10, center=True, default=values[8])
			# 상하 정렬
			self._add_combo(rowf, ["Top", "Middle", "Bottom"], width_chars=10, center=True, default=values[9])

	def _add_labeled_combo(self, parent, label, values, default=None, width_chars=8):
		frame = ctk.CTkFrame(parent, fg_color="transparent")
		frame.pack(side="left", padx=(0, 8))
		ctk.CTkLabel(frame, text=label).pack(side="left", padx=(0, 4))
		combo = ctk.CTkComboBox(frame, values=values, width=width_chars*9,
						fg_color=config.COLOR_THEME["widget"], text_color=config.COLOR_THEME["text"])
		combo.pack(side="left")
		if default:
			combo.set(default)
		return combo

	def _add_entry(self, parent, width_chars=8, center=False, default=""):
		entry = ctk.CTkEntry(parent, width=width_chars*9, fg_color=config.COLOR_THEME["widget"], text_color=config.COLOR_THEME["text"])
		entry.pack(side="left")
		if default:
			entry.insert(0, default)
		if center:
			try:
				entry.configure(justify="center")
			except Exception:
				pass
		return entry

	def _add_combo(self, parent, values, width_chars=8, center=False, default=None):
		combo = ctk.CTkComboBox(parent, values=values, width=width_chars*9,
						fg_color=config.COLOR_THEME["widget"], text_color=config.COLOR_THEME["text"])
		combo.pack(side="left")
		if default:
			combo.set(default)
		if center:
			try:
				combo.configure(justify="center")
			except Exception:
				pass
		return combo
