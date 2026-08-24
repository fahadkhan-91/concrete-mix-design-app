from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure


class ChartsWidget(QWidget):
    def __init__(self):
        super().__init__()

        layout = QHBoxLayout(self)

        # pie chart - mix composition
        self.pie_figure = Figure(figsize=(5, 4), facecolor="#262e3d")
        self.pie_canvas = FigureCanvasQTAgg(self.pie_figure)
        layout.addWidget(self.pie_canvas)

        # bar chart - cost breakdown
        self.bar_figure = Figure(figsize=(5, 4), facecolor="#262e3d")
        self.bar_canvas = FigureCanvasQTAgg(self.bar_figure)
        layout.addWidget(self.bar_canvas)

    def update_composition_chart(self, result):
        # dark theme ke sath match karne ke liye colors manually set kar rahe hain
        self.pie_figure.clear()
        ax = self.pie_figure.add_subplot(111)
        ax.set_facecolor("#262e3d")

        labels = ["Cement", "Water", "Fine Aggregate", "Coarse Aggregate"]
        values = [
            result["cement_field"],
            result["water_field"],
            result["fine_field"],
            result["coarse_field"],
        ]
        colors = ["#4f8cff", "#2ecc71", "#f39c12", "#9b59b6"]

        ax.pie(
            values, labels=labels, autopct="%1.1f%%", colors=colors,
            textprops={"color": "white", "fontsize": 9}
        )
        ax.set_title("Mix Composition (by weight)", color="white", fontsize=11)
        self.pie_figure.tight_layout()
        self.pie_canvas.draw()

    def update_cost_chart(self, cost_info):
        self.bar_figure.clear()
        ax = self.bar_figure.add_subplot(111)
        ax.set_facecolor("#1a2029")

        labels = ["Cement", "Fine Agg.", "Coarse Agg.", "Water"]
        values = [
            cost_info["cement_cost"],
            cost_info["fine_cost"],
            cost_info["coarse_cost"],
            cost_info["water_cost"],
        ]
        colors = ["#4f8cff", "#f39c12", "#9b59b6", "#2ecc71"]

        bars = ax.bar(labels, values, color=colors)
        ax.set_title("Cost Breakdown", color="white", fontsize=11)
        ax.tick_params(colors="white")
        for spine in ax.spines.values():
            spine.set_color("#38425a")

        # har bar ke upar value dikha do
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2, height, f'{height:.0f}',
                    ha="center", va="bottom", color="white", fontsize=8)

        self.bar_figure.tight_layout()
        self.bar_canvas.draw()
