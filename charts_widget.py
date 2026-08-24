from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure


class ChartsWidget(QWidget):
    def __init__(self):
        super().__init__()

        layout = QHBoxLayout(self)

        self.pie_figure = Figure(figsize=(5.5, 4.5), facecolor="#262e3d")
        self.pie_canvas = FigureCanvasQTAgg(self.pie_figure)
        layout.addWidget(self.pie_canvas)

        self.bar_figure = Figure(figsize=(5.5, 4.5), facecolor="#262e3d")
        self.bar_canvas = FigureCanvasQTAgg(self.bar_figure)
        layout.addWidget(self.bar_canvas)

    def update_composition_chart(self, result):
        self.pie_figure.clear()
        ax = self.pie_figure.add_subplot(111)
        ax.set_facecolor("#262e3d")

        # short labels use karo taake overlap na ho, legend mein full naam dikha denge
        short_labels = ["Cement", "Water", "Fine Agg.", "Coarse Agg."]
        values = [
            result["cement_field"],
            result["water_field"],
            result["fine_field"],
            result["coarse_field"],
        ]
        colors = ["#4f8cff", "#2ecc71", "#f39c12", "#9b59b6"]

        wedges, texts, autotexts = ax.pie(
            values, autopct="%1.1f%%", colors=colors, pctdistance=0.75,
            textprops={"color": "white", "fontsize": 9},
            wedgeprops={"edgecolor": "#1a2029", "linewidth": 1}
        )

        # labels ko pie ke bahar rakhne ke bajaye legend mein daal do - overlap ka masla khatam
        ax.legend(
            wedges, short_labels, loc="upper center", bbox_to_anchor=(0.5, -0.02),
            ncol=2, frameon=False, labelcolor="white", fontsize=9
        )
        ax.set_title("Mix Composition (by weight)", color="white", fontsize=12, pad=12)
        self.pie_figure.subplots_adjust(top=0.88, bottom=0.18)
        self.pie_canvas.draw()

    def update_cost_chart(self, cost_info):
        self.bar_figure.clear()
        ax = self.bar_figure.add_subplot(111)
        ax.set_facecolor("#1a2029")

        labels = ["Cement", "Fine\nAgg.", "Coarse\nAgg.", "Water"]
        values = [
            cost_info["cement_cost"],
            cost_info["fine_cost"],
            cost_info["coarse_cost"],
            cost_info["water_cost"],
        ]
        colors = ["#4f8cff", "#f39c12", "#9b59b6", "#2ecc71"]

        bars = ax.bar(labels, values, color=colors, width=0.6)
        ax.set_title("Cost Breakdown", color="white", fontsize=12, pad=12)
        ax.tick_params(colors="white", labelsize=9)
        for spine in ax.spines.values():
            spine.set_color("#38425a")

        # thora extra room upar rakho taake number labels cut na hon
        max_val = max(values) if values else 1
        ax.set_ylim(0, max_val * 1.15)

        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2, height, f'{height:.0f}',
                    ha="center", va="bottom", color="white", fontsize=9)

        self.bar_figure.subplots_adjust(top=0.88, bottom=0.15, left=0.12, right=0.95)
        self.bar_canvas.draw()

    def save_charts_as_images(self, pie_path, bar_path):
        """PDF report ke liye charts ko PNG files ke tor pe save karta hai."""
        self.pie_figure.savefig(pie_path, facecolor=self.pie_figure.get_facecolor(), dpi=150)
        self.bar_figure.savefig(bar_path, facecolor=self.bar_figure.get_facecolor(), dpi=150)
