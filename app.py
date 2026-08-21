import sys
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QComboBox, QPushButton, QTableWidget,
    QTableWidgetItem, QFrame, QHeaderView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from logic.mix_design import calculate_mix


class MixDesignApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Concrete Mix Design — ACI 211.1")
        self.resize(950, 650)
        self.build_ui()
        self.apply_styles()

    def build_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(25, 25, 25, 25)

        # left side - input form card
        form_card = QFrame()
        form_card.setObjectName("card")
        form_layout = QVBoxLayout(form_card)
        form_layout.setSpacing(14)

        title = QLabel("Mix Design Inputs")
        title.setObjectName("title")
        form_layout.addWidget(title)

        subtitle = QLabel("ACI 211.1 Standard Method")
        subtitle.setObjectName("subtitle")
        form_layout.addWidget(subtitle)

        grid = QGridLayout()
        grid.setVerticalSpacing(12)
        grid.setHorizontalSpacing(10)

        # target strength
        grid.addWidget(QLabel("Target Strength f'ck (MPa)"), 0, 0)
        self.fck_input = QLineEdit()
        self.fck_input.setPlaceholderText("e.g. 30")
        grid.addWidget(self.fck_input, 0, 1)

        # slump
        grid.addWidget(QLabel("Slump (mm)"), 1, 0)
        self.slump_input = QLineEdit()
        self.slump_input.setPlaceholderText("e.g. 100")
        grid.addWidget(self.slump_input, 1, 1)

        # max aggregate size
        grid.addWidget(QLabel("Max Aggregate Size (mm)"), 2, 0)
        self.agg_size_combo = QComboBox()
        self.agg_size_combo.addItems(["10", "20", "25", "40"])
        self.agg_size_combo.setCurrentText("20")
        grid.addWidget(self.agg_size_combo, 2, 1)

        # exposure
        grid.addWidget(QLabel("Exposure Condition"), 3, 0)
        self.exposure_combo = QComboBox()
        self.exposure_combo.addItems(["mild", "moderate", "severe"])
        grid.addWidget(self.exposure_combo, 3, 1)

        # fineness modulus
        grid.addWidget(QLabel("Fineness Modulus of Sand"), 4, 0)
        self.fm_input = QLineEdit()
        self.fm_input.setPlaceholderText("e.g. 2.6")
        grid.addWidget(self.fm_input, 4, 1)

        form_layout.addLayout(grid)

        # calculate button
        self.calc_btn = QPushButton("Calculate Mix Design")
        self.calc_btn.setObjectName("calcBtn")
        self.calc_btn.clicked.connect(self.on_calculate)
        form_layout.addWidget(self.calc_btn)

        # error label, hidden until something goes wrong
        self.error_label = QLabel("")
        self.error_label.setObjectName("errorLabel")
        self.error_label.setWordWrap(True)
        form_layout.addWidget(self.error_label)

        form_layout.addStretch()

        # right side - results card
        result_card = QFrame()
        result_card.setObjectName("card")
        result_layout = QVBoxLayout(result_card)

        result_title = QLabel("Mix Design Results")
        result_title.setObjectName("title")
        result_layout.addWidget(result_title)

        self.result_table = QTableWidget()
        self.result_table.setColumnCount(2)
        self.result_table.setHorizontalHeaderLabels(["Parameter", "Value"])
        self.result_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.result_table.verticalHeader().setVisible(False)
        self.result_table.setEditTriggers(QTableWidget.NoEditTriggers)
        result_layout.addWidget(self.result_table)

        main_layout.addWidget(form_card, 1)
        main_layout.addWidget(result_card, 1)

    def on_calculate(self):
        # pehle purana error clear kar do
        self.error_label.setText("")

        try:
            fck = float(self.fck_input.text())
            slump = float(self.slump_input.text())
            max_agg_size = int(self.agg_size_combo.currentText())
            exposure = self.exposure_combo.currentText()
            fm_sand = float(self.fm_input.text())
        except ValueError:
            self.error_label.setText("Sab fields sahi se bharo — numbers hi likhne hain.")
            return

        result = calculate_mix(fck, slump, max_agg_size, exposure, fm_sand)
        self.populate_results(result)

    def populate_results(self, result):
        rows = [
            ("Slump Category", result["slump_category"]),
            ("Water Content", f'{result["water"]} kg/m³'),
            ("W/C Ratio (strength-based)", result["wc_strength"]),
            ("W/C Ratio (exposure limit)", result["wc_limit"]),
            ("Final W/C Ratio Used", result["wc_final"]),
            ("Cement Content", f'{result["cement"]} kg/m³'),
            ("Coarse Aggregate Fraction", result["coarse_fraction"]),
            ("Coarse Aggregate", f'{result["coarse"]} kg/m³'),
            ("Fine Aggregate", f'{result["fine"]} kg/m³'),
            ("Air Content", f'{result["air_percent"]}%'),
        ]

        self.result_table.setRowCount(len(rows))
        for i, (label, value) in enumerate(rows):
            self.result_table.setItem(i, 0, QTableWidgetItem(label))
            self.result_table.setItem(i, 1, QTableWidgetItem(str(value)))

    def apply_styles(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #1e2530;
                font-family: Segoe UI;
                color: #e6e9ef;
            }
            #card {
                background-color: #262e3d;
                border-radius: 12px;
                padding: 20px;
            }
            #title {
                font-size: 20px;
                font-weight: bold;
                color: #ffffff;
            }
            #subtitle {
                font-size: 12px;
                color: #8b94a8;
                margin-bottom: 10px;
            }
            QLabel {
                font-size: 13px;
                color: #c4cad6;
            }
            QLineEdit, QComboBox {
                background-color: #1a2029;
                border: 1px solid #38425a;
                border-radius: 6px;
                padding: 8px;
                color: #ffffff;
                font-size: 13px;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 1px solid #4f8cff;
            }
            #calcBtn {
                background-color: #4f8cff;
                color: white;
                font-weight: bold;
                font-size: 14px;
                padding: 12px;
                border-radius: 8px;
                margin-top: 10px;
            }
            #calcBtn:hover {
                background-color: #3d76e0;
            }
            #errorLabel {
                color: #ff6b6b;
                font-size: 12px;
                margin-top: 6px;
            }
            QTableWidget {
                background-color: #1a2029;
                border: 1px solid #38425a;
                border-radius: 6px;
                gridline-color: #2c3547;
            }
            QHeaderView::section {
                background-color: #2c3547;
                color: #ffffff;
                padding: 6px;
                border: none;
                font-weight: bold;
            }
        """)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MixDesignApp()
    window.show()
    sys.exit(app.exec())
