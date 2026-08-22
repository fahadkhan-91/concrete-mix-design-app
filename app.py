import sys
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QComboBox, QPushButton, QTableWidget,
    QTableWidgetItem, QFrame, QHeaderView, QTabWidget
)
from PySide6.QtCore import Qt

from logic.mix_design import calculate_mix, compute_batch_quantities


class MixDesignApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Concrete Mix Design — ACI 211.1")
        self.resize(1050, 720)
        self.last_result = None
        self.build_ui()
        self.apply_styles()

    def build_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(25, 25, 25, 25)

        form_card = QFrame()
        form_card.setObjectName("card")
        form_layout = QVBoxLayout(form_card)
        form_layout.setSpacing(12)

        title = QLabel("Mix Design Inputs")
        title.setObjectName("title")
        form_layout.addWidget(title)

        subtitle = QLabel("ACI 211.1 Standard Method")
        subtitle.setObjectName("subtitle")
        form_layout.addWidget(subtitle)

        grid = QGridLayout()
        grid.setVerticalSpacing(10)
        grid.setHorizontalSpacing(10)

        grid.addWidget(QLabel("Target Strength f'ck (MPa)"), 0, 0)
        self.fck_input = QLineEdit()
        self.fck_input.setPlaceholderText("e.g. 30")
        grid.addWidget(self.fck_input, 0, 1)

        grid.addWidget(QLabel("Slump (mm)"), 1, 0)
        self.slump_input = QLineEdit()
        self.slump_input.setPlaceholderText("e.g. 100")
        grid.addWidget(self.slump_input, 1, 1)

        grid.addWidget(QLabel("Max Aggregate Size (mm)"), 2, 0)
        self.agg_size_combo = QComboBox()
        self.agg_size_combo.addItems(["10", "20", "25", "40"])
        self.agg_size_combo.setCurrentText("20")
        grid.addWidget(self.agg_size_combo, 2, 1)

        grid.addWidget(QLabel("Exposure Condition"), 3, 0)
        self.exposure_combo = QComboBox()
        self.exposure_combo.addItems(["mild", "moderate", "severe"])
        grid.addWidget(self.exposure_combo, 3, 1)

        grid.addWidget(QLabel("Fineness Modulus of Sand"), 4, 0)
        self.fm_input = QLineEdit()
        self.fm_input.setPlaceholderText("e.g. 2.6")
        grid.addWidget(self.fm_input, 4, 1)

        form_layout.addLayout(grid)

        moisture_label = QLabel("Aggregate Moisture Correction (optional, 0 se start karo)")
        moisture_label.setObjectName("sectionLabel")
        form_layout.addWidget(moisture_label)

        moisture_grid = QGridLayout()
        moisture_grid.setVerticalSpacing(10)
        moisture_grid.setHorizontalSpacing(10)

        moisture_grid.addWidget(QLabel("Fine Agg. Moisture (%)"), 0, 0)
        self.fine_moisture_input = QLineEdit("0")
        moisture_grid.addWidget(self.fine_moisture_input, 0, 1)

        moisture_grid.addWidget(QLabel("Fine Agg. Absorption (%)"), 1, 0)
        self.fine_absorption_input = QLineEdit("0")
        moisture_grid.addWidget(self.fine_absorption_input, 1, 1)

        moisture_grid.addWidget(QLabel("Coarse Agg. Moisture (%)"), 2, 0)
        self.coarse_moisture_input = QLineEdit("0")
        moisture_grid.addWidget(self.coarse_moisture_input, 2, 1)

        moisture_grid.addWidget(QLabel("Coarse Agg. Absorption (%)"), 3, 0)
        self.coarse_absorption_input = QLineEdit("0")
        moisture_grid.addWidget(self.coarse_absorption_input, 3, 1)

        form_layout.addLayout(moisture_grid)

        batch_label = QLabel("Batch / Site Quantity")
        batch_label.setObjectName("sectionLabel")
        form_layout.addWidget(batch_label)

        batch_grid = QGridLayout()
        batch_grid.setVerticalSpacing(10)
        batch_grid.setHorizontalSpacing(10)

        batch_grid.addWidget(QLabel("Total Volume Needed (m³)"), 0, 0)
        self.volume_input = QLineEdit("1")
        batch_grid.addWidget(self.volume_input, 0, 1)

        batch_grid.addWidget(QLabel("Cement Bag Weight (kg)"), 1, 0)
        self.bag_weight_input = QLineEdit("50")
        batch_grid.addWidget(self.bag_weight_input, 1, 1)

        form_layout.addLayout(batch_grid)

        self.calc_btn = QPushButton("Calculate Mix Design")
        self.calc_btn.setObjectName("calcBtn")
        self.calc_btn.clicked.connect(self.on_calculate)
        form_layout.addWidget(self.calc_btn)

        self.error_label = QLabel("")
        self.error_label.setObjectName("errorLabel")
        self.error_label.setWordWrap(True)
        form_layout.addWidget(self.error_label)

        form_layout.addStretch()

        result_card = QFrame()
        result_card.setObjectName("card")
        result_layout = QVBoxLayout(result_card)

        result_title = QLabel("Mix Design Results")
        result_title.setObjectName("title")
        result_layout.addWidget(result_title)

        self.tabs = QTabWidget()

        self.batch_design_table = self.make_result_table()
        self.field_table = self.make_result_table()
        self.site_batch_table = self.make_result_table()

        self.tabs.addTab(self.batch_design_table, "Batch (Dry) Quantities")
        self.tabs.addTab(self.field_table, "Field (Moisture Adjusted)")
        self.tabs.addTab(self.site_batch_table, "Site Batching")

        result_layout.addWidget(self.tabs)

        main_layout.addWidget(form_card, 1)
        main_layout.addWidget(result_card, 1)

    def make_result_table(self):
        table = QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["Parameter", "Value"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        return table

    def on_calculate(self):
        self.error_label.setText("")

        try:
            fck = float(self.fck_input.text())
            slump = float(self.slump_input.text())
            max_agg_size = int(self.agg_size_combo.currentText())
            exposure = self.exposure_combo.currentText()
            fm_sand = float(self.fm_input.text())

            fine_moisture = float(self.fine_moisture_input.text() or 0)
            fine_absorption = float(self.fine_absorption_input.text() or 0)
            coarse_moisture = float(self.coarse_moisture_input.text() or 0)
            coarse_absorption = float(self.coarse_absorption_input.text() or 0)

            volume_m3 = float(self.volume_input.text() or 1)
            bag_weight = float(self.bag_weight_input.text() or 50)
        except ValueError:
            self.error_label.setText("Sab fields sahi se bharo — numbers hi likhne hain.")
            return

        result = calculate_mix(
            fck, slump, max_agg_size, exposure, fm_sand,
            fine_moisture, fine_absorption,
            coarse_moisture, coarse_absorption
        )
        self.last_result = result

        batch_info = compute_batch_quantities(result, volume_m3, bag_weight)

        self.populate_results(result, batch_info)

    def populate_results(self, result, batch_info):
        common_rows = [
            ("Slump Category", result["slump_category"]),
            ("W/C Ratio (strength-based)", result["wc_strength"]),
            ("W/C Ratio (exposure limit)", result["wc_limit"]),
            ("Final W/C Ratio Used", result["wc_final"]),
            ("Coarse Aggregate Fraction", result["coarse_fraction"]),
            ("Air Content", f'{result["air_percent"]}%'),
        ]

        batch_rows = common_rows + [
            ("Water (batch)", f'{result["water_batch"]} kg/m³'),
            ("Cement (batch)", f'{result["cement_batch"]} kg/m³'),
            ("Fine Aggregate (batch)", f'{result["fine_batch"]} kg/m³'),
            ("Coarse Aggregate (batch)", f'{result["coarse_batch"]} kg/m³'),
        ]

        field_rows = common_rows + [
            ("Water (field, adjusted)", f'{result["water_field"]} kg/m³'),
            ("Cement (field)", f'{result["cement_field"]} kg/m³'),
            ("Fine Aggregate (field)", f'{result["fine_field"]} kg/m³'),
            ("Coarse Aggregate (field)", f'{result["coarse_field"]} kg/m³'),
        ]

        site_rows = [
            ("Cement Bags per m³", batch_info["bags_per_m3"]),
            ("Water per Bag", f'{batch_info["water_per_bag"]} kg'),
            ("Fine Aggregate per Bag", f'{batch_info["fine_per_bag"]} kg'),
            ("Coarse Aggregate per Bag", f'{batch_info["coarse_per_bag"]} kg'),
            ("— Total for Requested Volume —", f'{batch_info["volume_m3"]} m³'),
            ("Total Cement Bags", batch_info["total_bags"]),
            ("Total Cement", f'{batch_info["total_cement_kg"]} kg'),
            ("Total Water", f'{batch_info["total_water_kg"]} kg'),
            ("Total Fine Aggregate", f'{batch_info["total_fine_kg"]} kg'),
            ("Total Coarse Aggregate", f'{batch_info["total_coarse_kg"]} kg'),
        ]

        self.fill_table(self.batch_design_table, batch_rows)
        self.fill_table(self.field_table, field_rows)
        self.fill_table(self.site_batch_table, site_rows)

    def fill_table(self, table, rows):
        table.setRowCount(len(rows))
        for i, (label, value) in enumerate(rows):
            table.setItem(i, 0, QTableWidgetItem(str(label)))
            table.setItem(i, 1, QTableWidgetItem(str(value)))

    def apply_styles(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #1e2530;
                font-family: Segoe UI;
                font-size: 13px;
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
                margin-bottom: 6px;
            }
            #sectionLabel {
                font-size: 13px;
                font-weight: bold;
                color: #4f8cff;
                margin-top: 8px;
            }
            QLabel {
                font-size: 13px;
                color: #c4cad6;
                background: transparent;
            }
            QLineEdit {
                background-color: #ffffff;
                border: 1px solid #38425a;
                border-radius: 6px;
                padding: 6px 8px;
                color: #000000;
                font-size: 13px;
                min-height: 22px;
            }
            QLineEdit:focus {
                border: 1px solid #4f8cff;
            }
            QComboBox {
                background-color: #ffffff;
                border: 1px solid #38425a;
                border-radius: 6px;
                padding: 6px 8px;
                color: #000000;
                font-size: 13px;
                min-height: 22px;
            }
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                color: #000000;
                selection-background-color: #4f8cff;
                selection-color: #ffffff;
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
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #2c3547;
                color: #ffffff;
                padding: 6px;
                border: none;
                font-weight: bold;
            }
            QTabBar::tab {
                background-color: #1a2029;
                color: #8b94a8;
                padding: 8px 16px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }
            QTabBar::tab:selected {
                background-color: #4f8cff;
                color: white;
            }
        """)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")   # ye line important hai - windows native style kabhi kabhi text color ignore kar deta hai
    window = MixDesignApp()
    window.show()
    sys.exit(app.exec())
