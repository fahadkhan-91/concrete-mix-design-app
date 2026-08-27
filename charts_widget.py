from PySide6.QtWidgets import QWidget, QGridLayout
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

# consistent color palette - har material ka rang hamesha same rahega har chart mein
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

        layout = QGridLayout(self)
        layout.setSpacing(15)

        # 4 charts, 2x2 grid - sab consistent size ke
        self.pie_figure = Figure(figsize=(5, 4), facecolor=BG_DARK)
        self.pie_canvas = FigureCanvasQTAgg(self.pie_figure)
        layout.addWidget(self.pie_canvas, 0, 0)

        self.bar_figure = Figure(figsize=(5, 4), facecolor=BG_DARK)
        self.bar_canvas = FigureCanvasQTAgg(self.bar_figure)
        layout.addWidget(self.bar_canvas, 0, 1)

        self.compare_figure = Figure(figsize=(5, 4), facecolor=BG_DARK)
        self.compare_canvas = FigureCanvasQTAgg(self.compare_figure)
        layout.addWidget(self.compare_canvas, 1, 0)

        self.wc_figure = Figure(figsize=(5, 4), facecolor=BG_DARK)
        self.wc_canvas = FigureCanvasQTAgg(self.wc_figure)
        layout.addWidget(self.wc_canvas, 1, 1)

    def _style_axis(self, ax, facecolor):
        ax.set_facecolor(facecolor)
        ax.tick_params(colors=TEXT_COLOR, labelsize=8)
        for spine in ax.spines.values():
            spine.set_color(GRID_COLOR)
        ax.grid(axis="y", color=GRID_COLOR, linewidth=0.5, alpha=0.5)
        ax.set_axisbelow(True)

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
            textprops={"color": "white", "fontsize": 9},
            wedgeprops={"edgecolor": BG_DARKER, "linewidth": 1}
        )
        ax.legend(
            wedges, labels, loc="upper center", bbox_to_anchor=(0.5, -0.02),
            ncol=2, frameon=False, labelcolor="white", fontsize=8
        )
        ax.set_title("Mix Composition (by weight)", color="white", fontsize=11, pad=10)
        self.pie_figure.subplots_adjust(top=0.88, bottom=0.2)
        self.pie_canvas.draw()

    # ---------- Chart 2: Cost Breakdown Bar ----------
    def update_cost_chart(self, cost_info):
        self.bar_figure.clear()
        ax = self.bar_figure.add_subplot(111)
        self._style_axis(ax, BG_DARKER)

        labels = ["Cement", "Fine\nAgg.", "Coarse\nAgg.", "Water"]
        values = [
            cost_info["cement_cost"],
            cost_info["fine_cost"],
            cost_info["coarse_cost"],
            cost_info["water_cost"],
        ]
        colors = [COLOR_CEMENT, COLOR_FINE, COLOR_COARSE, COLOR_WATER]

        bars = ax.bar(labels, values, color=colors, width=0.6)
        ax.set_title("Cost Breakdown", color="white", fontsize=11, pad=10)

        max_val = max(values) if values and max(values) > 0 else 1
        ax.set_ylim(0, max_val * 1.15)

        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2, height, f'{height:,.0f}',
                    ha="center", va="bottom", color="white", fontsize=8)

        self.bar_figure.subplots_adjust(top=0.88, bottom=0.15, left=0.15, right=0.95)
        self.bar_canvas.draw()

    # ---------- Chart 3: Batch vs Field Comparison ----------
    def update_batch_vs_field_chart(self, result):
        self.compare_figure.clear()
        ax = self.compare_figure.add_subplot(111)
        self._style_axis(ax, BG_DARKER)

        categories = ["Water", "Cement", "Fine\nAgg.", "Coarse\nAgg."]
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
        ax.set_title("Batch vs Field Quantities (kg/m³)", color="white", fontsize=11, pad=10)
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2,
                  frameon=False, labelcolor="white", fontsize=8)

        self.compare_figure.subplots_adjust(top=0.88, bottom=0.22, left=0.12, right=0.95)
        self.compare_canvas.draw()

    # ---------- Chart 4: W/C Ratio Comparison ----------
    def update_wc_ratio_chart(self, result):
        self.wc_figure.clear()
        ax = self.wc_figure.add_subplot(111)
        self._style_axis(ax, BG_DARKER)

        labels = ["Strength-\nBased", "Exposure\nLimit", "Final\nUsed"]
        values = [result["wc_strength"], result["wc_limit"], result["wc_final"]]
        colors = ["#5b6b8c", "#e74c3c", COLOR_CEMENT]

        bars = ax.barh(labels, values, color=colors, height=0.5)
        ax.set_title("Water/Cement Ratio Comparison", color="white", fontsize=11, pad=10)
        ax.set_xlim(0, max(values) * 1.3)

        for bar in bars:
            width = bar.get_width()
            ax.text(width, bar.get_y() + bar.get_height()/2, f'  {width:.2f}',
                    va="center", ha="left", color="white", fontsize=9)

        self.wc_figure.subplots_adjust(top=0.85, bottom=0.15, left=0.22, right=0.9)
        self.wc_canvas.draw()

    def save_charts_as_images(self, pie_path, bar_path, compare_path=None, wc_path=None):
        """PDF report ke liye charts ko PNG files ke tor pe save karta hai."""
        self.pie_figure.savefig(pie_path, facecolor=self.pie_figure.get_facecolor(), dpi=150)
        self.bar_figure.savefig(bar_path, facecolor=self.bar_figure.get_facecolor(), dpi=150)
        if compare_path:
            self.compare_figure.savefig(compare_path, facecolor=self.compare_figure.get_facecolor(), dpi=150)
        if wc_path:
            self.wc_figure.savefig(wc_path, facecolor=self.wc_figure.get_facecolor(), dpi=150)
