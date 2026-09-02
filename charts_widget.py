from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget, QPushButton
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import mplcursors

COLOR_CEMENT = "#4f8cff"
COLOR_WATER = "#2ecc71"
COLOR_FINE = "#f39c12"
COLOR_COARSE = "#9b59b6"

BG_DARK = "#262e3d"
BG_DARKER = "#1a2029"
GRID_COLOR = "#38425a"
TEXT_COLOR = "white"


class ChartsWidget(QWidget):
    def __init__(self):
        super().__init__()

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)

        nav_row = QHBoxLayout()
        nav_row.setSpacing(8)

        self.nav_buttons = []
        chart_names = ["Mix Composition", "Cost Breakdown", "Batch vs Field", "W/C Ratio"]
        for i, name in enumerate(chart_names):
            btn = QPushButton(name)
            btn.setObjectName("chartNavBtn")
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, idx=i: self.show_chart(idx))
            nav_row.addWidget(btn)
            self.nav_buttons.append(btn)

        nav_row.addStretch()

        self.reset_btn = QPushButton("↺  Reset View")
        self.reset_btn.setObjectName("resetViewBtn")
        self.reset_btn.clicked.connect(self.reset_current_view)
        nav_row.addWidget(self.reset_btn)

        main_layout.addLayout(nav_row)

        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack)

        self.pie_figure = Figure(figsize=(8, 6), facecolor=BG_DARK)
        self.pie_canvas = FigureCanvasQTAgg(self.pie_figure)
        self.stack.addWidget(self.pie_canvas)

        self.bar_figure = Figure(figsize=(8, 6), facecolor=BG_DARK)
        self.bar_canvas = FigureCanvasQTAgg(self.bar_figure)
        self.stack.addWidget(self.bar_canvas)

        self.compare_figure = Figure(figsize=(8, 6), facecolor=BG_DARK)
        self.compare_canvas = FigureCanvasQTAgg(self.compare_figure)
        self.stack.addWidget(self.compare_canvas)

        self.wc_figure = Figure(figsize=(8, 6), facecolor=BG_DARK)
        self.wc_canvas = FigureCanvasQTAgg(self.wc_figure)
        self.stack.addWidget(self.wc_canvas)

        # zoom sirf bar/compare/wc charts pe - pie chart ko zoom karne se koi fayda nahi,
        # ulta distort ho jata hai isliye usay scroll-zoom se exclude kar diya
        self.bar_canvas.mpl_connect("scroll_event", self._on_scroll_zoom)
        self.compare_canvas.mpl_connect("scroll_event", self._on_scroll_zoom)
        self.wc_canvas.mpl_connect("scroll_event", self._on_scroll_zoom)

        self._active_cursors = []
        # har chart ka axis aur uska original (default) view store karte hain, reset button ke liye
        self._axes = {}
        self._original_limits = {}

        self._apply_nav_styles()
        self.show_chart(0)

    def show_chart(self, index):
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)

    def reset_current_view(self):
        idx = self.stack.currentIndex()
        ax = self._axes.get(idx)
        limits = self._original_limits.get(idx)
        if ax is None or limits is None:
            return
        ax.set_xlim(limits[0])
        ax.set_ylim(limits[1])
        ax.figure.canvas.draw_idle()

    def _apply_nav_styles(self):
        self.setStyleSheet("""
            QPushButton#chartNavBtn {
                background-color: #1a2029;
                color: #8b94a8;
                border: 1px solid #38425a;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton#chartNavBtn:hover {
                background-color: #2c3547;
            }
            QPushButton#chartNavBtn:checked {
                background-color: #4f8cff;
                color: white;
                border: 1px solid #4f8cff;
            }
            QPushButton#resetViewBtn {
                background-color: #2c3547;
                color: #c4cad6;
                border: 1px solid #38425a;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton#resetViewBtn:hover {
                background-color: #38425a;
                color: white;
            }
        """)

    def _on_scroll_zoom(self, event):
        ax = event.inaxes
        if ax is None:
            return

        scale_factor = 0.85 if event.button == "up" else 1.15

        cur_xlim = ax.get_xlim()
        cur_ylim = ax.get_ylim()
        xdata, ydata = event.xdata, event.ydata
        if xdata is None or ydata is None:
            return

        new_width = (cur_xlim[1] - cur_xlim[0]) * scale_factor
        new_height = (cur_ylim[1] - cur_ylim[0]) * scale_factor

        relx = (cur_xlim[1] - xdata) / (cur_xlim[1] - cur_xlim[0])
        rely = (cur_ylim[1] - ydata) / (cur_ylim[1] - cur_ylim[0])

        ax.set_xlim([xdata - new_width * (1 - relx), xdata + new_width * relx])
        ax.set_ylim([ydata - new_height * (1 - rely), ydata + new_height * rely])
        ax.figure.canvas.draw_idle()

    def _clear_cursors(self):
        for cursor in self._active_cursors:
            try:
                cursor.remove()
            except Exception:
                pass
        self._active_cursors = []

    def _style_axis(self, ax, facecolor):
        ax.set_facecolor(facecolor)
        ax.tick_params(colors=TEXT_COLOR, labelsize=9)
        for spine in ax.spines.values():
            spine.set_color(GRID_COLOR)
        ax.grid(axis="y", color=GRID_COLOR, linewidth=0.5, alpha=0.5)
        ax.set_axisbelow(True)

    def _style_tooltip(self, cursor):
        cursor.connect("add", lambda sel: sel.annotation.get_bbox_patch().set(
            fc="#1a2029", ec="#4f8cff", alpha=0.95
        ))
        cursor.connect("add", lambda sel: sel.annotation.set_color("white"))

    # ---------- Chart 1: Mix Composition Pie ----------
    def update_composition_chart(self, result):
        self.pie_figure.clear()
        ax = self.pie_figure.add_subplot(111)
        ax.set_facecolor(BG_DARK)

        labels = ["Cement", "Water", "Fine Agg.", "Coarse Agg."]
        values = [
            result["cement_field"],
            result["water_field"],
            result["fine_field"],
            result["coarse_field"],
        ]
        colors = [COLOR_CEMENT, COLOR_WATER, COLOR_FINE, COLOR_COARSE]

        wedges, texts, autotexts = ax.pie(
            values, autopct="%1.1f%%", colors=colors, pctdistance=0.75,
            textprops={"color": "white", "fontsize": 11},
            wedgeprops={"edgecolor": BG_DARKER, "linewidth": 1.5}
        )
        ax.legend(
            wedges, labels, loc="upper center", bbox_to_anchor=(0.5, -0.02),
            ncol=4, frameon=False, labelcolor="white", fontsize=10
        )
        ax.set_title("Mix Composition (by weight)", color="white", fontsize=14, pad=14)
        self.pie_figure.subplots_adjust(top=0.90, bottom=0.12)

        cursor = mplcursors.cursor(wedges, hover=True)
        cursor.connect("add", lambda sel: sel.annotation.set_text(
            f"{labels[sel.index]}: {values[sel.index]:.1f} kg/m³"
        ))
        self._style_tooltip(cursor)
        self._active_cursors.append(cursor)

        self._axes[0] = ax
        self._original_limits[0] = (ax.get_xlim(), ax.get_ylim())

        self.pie_canvas.draw()

    # ---------- Chart 2: Cost Breakdown Bar ----------
    def update_cost_chart(self, cost_info):
        self.bar_figure.clear()
        ax = self.bar_figure.add_subplot(111)
        self._style_axis(ax, BG_DARKER)

        labels = ["Cement", "Fine Agg.", "Coarse Agg.", "Water"]
        values = [
            cost_info["cement_cost"],
            cost_info["fine_cost"],
            cost_info["coarse_cost"],
            cost_info["water_cost"],
        ]
        colors = [COLOR_CEMENT, COLOR_FINE, COLOR_COARSE, COLOR_WATER]

        bars = ax.bar(labels, values, color=colors, width=0.55)
        ax.set_title("Cost Breakdown", color="white", fontsize=14, pad=14)

        max_val = max(values) if values and max(values) > 0 else 1
        ax.set_ylim(0, max_val * 1.15)

        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2, height, f'{height:,.0f}',
                    ha="center", va="bottom", color="white", fontsize=10)

        self.bar_figure.subplots_adjust(top=0.90, bottom=0.1, left=0.1, right=0.95)

        cursor = mplcursors.cursor(bars, hover=True)
        cursor.connect("add", lambda sel: sel.annotation.set_text(
            f"{labels[sel.index]}: {values[sel.index]:,.0f}"
        ))
        self._style_tooltip(cursor)
        self._active_cursors.append(cursor)

        self._axes[1] = ax
        self._original_limits[1] = (ax.get_xlim(), ax.get_ylim())

        self.bar_canvas.draw()

    # ---------- Chart 3: Batch vs Field Comparison ----------
    def update_batch_vs_field_chart(self, result):
        self.compare_figure.clear()
        ax = self.compare_figure.add_subplot(111)
        self._style_axis(ax, BG_DARKER)

        categories = ["Water", "Cement", "Fine Agg.", "Coarse Agg."]
        batch_values = [
            result["water_batch"], result["cement_batch"],
            result["fine_batch"], result["coarse_batch"]
        ]
        field_values = [
            result["water_field"], result["cement_field"],
            result["fine_field"], result["coarse_field"]
        ]

        x = range(len(categories))
        width = 0.35

        bars1 = ax.bar([i - width/2 for i in x], batch_values, width,
                        label="Batch (Dry)", color="#5b6b8c")
        bars2 = ax.bar([i + width/2 for i in x], field_values, width,
                        label="Field (Moisture Adjusted)", color=COLOR_CEMENT)

        ax.set_xticks(list(x))
        ax.set_xticklabels(categories)
        ax.set_title("Batch vs Field Quantities (kg/m³)", color="white", fontsize=14, pad=14)
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=2,
                  frameon=False, labelcolor="white", fontsize=10)

        self.compare_figure.subplots_adjust(top=0.90, bottom=0.16, left=0.1, right=0.95)

        cursor1 = mplcursors.cursor(bars1, hover=True)
        cursor1.connect("add", lambda sel: sel.annotation.set_text(
            f"{categories[sel.index]} (Batch): {batch_values[sel.index]:.1f} kg/m³"
        ))
        self._style_tooltip(cursor1)
        self._active_cursors.append(cursor1)

        cursor2 = mplcursors.cursor(bars2, hover=True)
        cursor2.connect("add", lambda sel: sel.annotation.set_text(
            f"{categories[sel.index]} (Field): {field_values[sel.index]:.1f} kg/m³"
        ))
        self._style_tooltip(cursor2)
        self._active_cursors.append(cursor2)

        self._axes[2] = ax
        self._original_limits[2] = (ax.get_xlim(), ax.get_ylim())

        self.compare_canvas.draw()

    # ---------- Chart 4: W/C Ratio Comparison ----------
    def update_wc_ratio_chart(self, result):
        self.wc_figure.clear()
        ax = self.wc_figure.add_subplot(111)
        self._style_axis(ax, BG_DARKER)

        labels = ["Strength-Based", "Exposure Limit", "Final Used"]
        values = [result["wc_strength"], result["wc_limit"], result["wc_final"]]
        colors = ["#5b6b8c", "#e74c3c", COLOR_CEMENT]

        bars = ax.barh(labels, values, color=colors, height=0.5)
        ax.set_title("Water/Cement Ratio Comparison", color="white", fontsize=14, pad=14)
        ax.set_xlim(0, max(values) * 1.3)

        for bar in bars:
            width = bar.get_width()
            ax.text(width, bar.get_y() + bar.get_height()/2, f'  {width:.2f}',
                    va="center", ha="left", color="white", fontsize=11)

        self.wc_figure.subplots_adjust(top=0.88, bottom=0.1, left=0.2, right=0.9)

        cursor = mplcursors.cursor(bars, hover=True)
        cursor.connect("add", lambda sel: sel.annotation.set_text(
            f"{labels[sel.index]}: {values[sel.index]:.3f}"
        ))
        self._style_tooltip(cursor)
        self._active_cursors.append(cursor)

        self._axes[3] = ax
        self._original_limits[3] = (ax.get_xlim(), ax.get_ylim())

        self.wc_canvas.draw()

    def save_charts_as_images(self, pie_path, bar_path, compare_path=None, wc_path=None):
        """PDF report ke liye charts ko PNG files ke tor pe save karta hai."""
        self.pie_figure.savefig(pie_path, facecolor=self.pie_figure.get_facecolor(), dpi=150)
        self.bar_figure.savefig(bar_path, facecolor=self.bar_figure.get_facecolor(), dpi=150)
        if compare_path:
            self.compare_figure.savefig(compare_path, facecolor=self.compare_figure.get_facecolor(), dpi=150)
        if wc_path:
            self.wc_figure.savefig(wc_path, facecolor=self.wc_figure.get_facecolor(), dpi=150)
