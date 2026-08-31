import sys
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QComboBox, QPushButton, QTableWidget,
    QTableWidgetItem, QFrame, QHeaderView, QTabWidget, QListWidget,
    QListWidgetItem, QMessageBox, QScrollArea, QFileDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from logic.mix_design import (
    calculate_mix as calculate_mix_aci,
    compute_batch_quantities, compute_cost_estimate, adjust_trial_mix
)
from logic.is10262 import calculate_mix as calculate_mix_is
from database import init_db, save_project, get_all_projects, get_project, delete_project, search_projects
from report_generator import generate_pdf_report
from charts_widget import ChartsWidget


class MixDesignApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Concrete Mix Design — ACI 211.1 / IS 10262")
        self.setWindowIcon(QIcon("app_icon.ico"))
        self.resize(1200, 880)
        self.last_result = None
        self.last_batch_info = None
        self.last_cost_info = None
        self.last_trial_result = None

        init_db()

        self.build_ui()
        self.apply_styles()
        self.refresh_projects_list()

    def build_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(25, 25, 25, 25)

        form_scroll = QScrollArea()
        form_scroll.setWidgetResizable(True)
        form_scroll.setObjectName("formScroll")

        form_card = QFrame()
        form_card.setObjectName("card")
        form_layout = QVBoxLayout(form_card)
        form_layout.setSpacing(14)

        title = QLabel("Mix Design Inputs")
        title.setObjectName("title")
        form_layout.addWidget(title)

        subtitle = QLabel("Choose a design method below")
        subtitle.setObjectName("subtitle")
        form_layout.addWidget(subtitle)

        # design method selector - drives which calculation engine runs
        method_label = QLabel("Design Method")
        method_label.setObjectName("sectionLabel")
        form_layout.addWidget(method_label)

        self.method_combo = QComboBox()
        self.method_combo.addItems(["ACI 211.1", "IS 10262"])
        self.method_combo.currentTextChanged.connect(self.on_method_changed)
        form_layout.addWidget(self.method_combo)

        grid = QGridLayout()
        grid.setVerticalSpacing(12)
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
        self.agg_size_combo.addItems(["10", "20", "40"])
        self.agg_size_combo.setCurrentText("20")
        grid.addWidget(self.agg_size_combo, 2, 1)

        grid.addWidget(QLabel("Exposure Condition"), 3, 0)
        self.exposure_combo = QComboBox()
        # 5 categories total - ACI only formally uses first 3, IS uses all 5
        self.exposure_combo.addItems(["mild", "moderate", "severe", "very_severe", "extreme"])
        grid.addWidget(self.exposure_combo, 3, 1)

        grid.addWidget(QLabel("Fineness Modulus of Sand (ACI)"), 4, 0)
        self.fm_input = QLineEdit()
        self.fm_input.setPlaceholderText("e.g. 2.6")
        grid.addWidget(self.fm_input, 4, 1)

        grid.addWidget(QLabel("Sand Zone (IS 10262)"), 5, 0)
        self.zone_combo = QComboBox()
        self.zone_combo.addItems(["I", "II", "III", "IV"])
        self.zone_combo.setCurrentText("II")
        grid.addWidget(self.zone_combo, 5, 1)

        form_layout.addLayout(grid)

        moisture_label = QLabel("Aggregate Moisture Correction (optional, defaults to 0)")
        moisture_label.setObjectName("sectionLabel")
        form_layout.addWidget(moisture_label)

        moisture_grid = QGridLayout()
        moisture_grid.setVerticalSpacing(12)
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
        batch_grid.setVerticalSpacing(12)
        batch_grid.setHorizontalSpacing(10)

        batch_grid.addWidget(QLabel("Total Volume Needed (m³)"), 0, 0)
        self.volume_input = QLineEdit("1")
        batch_grid.addWidget(self.volume_input, 0, 1)

        batch_grid.addWidget(QLabel("Cement Bag Weight (kg)"), 1, 0)
        self.bag_weight_input = QLineEdit("50")
        batch_grid.addWidget(self.bag_weight_input, 1, 1)

        form_layout.addLayout(batch_grid)

        cost_label = QLabel("Material Rates (for cost estimation)")
        cost_label.setObjectName("sectionLabel")
        form_layout.addWidget(cost_label)

        cost_grid = QGridLayout()
        cost_grid.setVerticalSpacing(12)
        cost_grid.setHorizontalSpacing(10)

        cost_grid.addWidget(QLabel("Cement Rate (per bag)"), 0, 0)
        self.cement_rate_input = QLineEdit("0")
        cost_grid.addWidget(self.cement_rate_input, 0, 1)

        cost_grid.addWidget(QLabel("Fine Aggregate Rate (per kg)"), 1, 0)
        self.fine_rate_input = QLineEdit("0")
        cost_grid.addWidget(self.fine_rate_input, 1, 1)

        cost_grid.addWidget(QLabel("Coarse Aggregate Rate (per kg)"), 2, 0)
        self.coarse_rate_input = QLineEdit("0")
        cost_grid.addWidget(self.coarse_rate_input, 2, 1)

        cost_grid.addWidget(QLabel("Water Rate (per liter, optional)"), 3, 0)
        self.water_rate_input = QLineEdit("0")
        cost_grid.addWidget(self.water_rate_input, 3, 1)

        form_layout.addLayout(cost_grid)

        trial_label = QLabel("Trial Mix Adjustment (after site trial batch)")
        trial_label.setObjectName("sectionLabel")
        form_layout.addWidget(trial_label)

        trial_grid = QGridLayout()
        trial_grid.setVerticalSpacing(12)
        trial_grid.setHorizontalSpacing(10)

        trial_grid.addWidget(QLabel("Actual Measured Slump (mm)"), 0, 0)
        self.actual_slump_input = QLineEdit()
        self.actual_slump_input.setPlaceholderText("e.g. 80")
        trial_grid.addWidget(self.actual_slump_input, 0, 1)

        trial_grid.addWidget(QLabel("Water Adjustment Rate (kg per 10mm)"), 1, 0)
        self.water_adj_rate_input = QLineEdit("2.5")
        trial_grid.addWidget(self.water_adj_rate_input, 1, 1)

        form_layout.addLayout(trial_grid)

        self.trial_btn = QPushButton("🔧  Compute Trial Adjustment")
        self.trial_btn.setObjectName("trialBtn")
        self.trial_btn.clicked.connect(self.on_trial_adjust)
        form_layout.addWidget(self.trial_btn)

        save_label = QLabel("Project Name (for saving / report)")
        save_label.setObjectName("sectionLabel")
        form_layout.addWidget(save_label)

        self.project_name_input = QLineEdit()
        self.project_name_input.setPlaceholderText("e.g. Site A - Column Mix")
        form_layout.addWidget(self.project_name_input)

        action_row = QHBoxLayout()

        self.save_btn = QPushButton("💾  Save Project")
        self.save_btn.setObjectName("saveBtn")
        self.save_btn.clicked.connect(self.on_save_project)
        action_row.addWidget(self.save_btn)

        self.pdf_btn = QPushButton("📄  Export PDF Report")
        self.pdf_btn.setObjectName("pdfBtn")
        self.pdf_btn.clicked.connect(self.on_export_pdf)
        action_row.addWidget(self.pdf_btn)

        form_layout.addLayout(action_row)

        self.calc_btn = QPushButton("🧮  Calculate Mix Design")
        self.calc_btn.setObjectName("calcBtn")
        self.calc_btn.clicked.connect(self.on_calculate)
        form_layout.addWidget(self.calc_btn)

        self.error_label = QLabel("")
        self.error_label.setObjectName("errorLabel")
        self.error_label.setWordWrap(True)
        form_layout.addWidget(self.error_label)

        form_layout.addStretch()

        form_scroll.setWidget(form_card)

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
        self.cost_table = self.make_result_table()
        self.trial_table = self.make_result_table()
        self.charts_widget = ChartsWidget()
        self.projects_tab = self.build_projects_tab()

        self.tabs.addTab(self.batch_design_table, "Batch (Dry) Quantities")
        self.tabs.addTab(self.field_table, "Field (Moisture Adjusted)")
        self.tabs.addTab(self.site_batch_table, "Site Batching")
        self.tabs.addTab(self.cost_table, "Cost Estimation")
        self.tabs.addTab(self.trial_table, "Trial Mix Adjustment")
        self.tabs.addTab(self.charts_widget, "Charts")
        self.tabs.addTab(self.projects_tab, "Saved Projects")

        result_layout.addWidget(self.tabs)

        main_layout.addWidget(form_scroll, 1)
        main_layout.addWidget(result_card, 1)

        self.on_method_changed(self.method_combo.currentText())

    def on_method_changed(self, method_text):
        # dono fields hamesha visible rehte hain, bas placeholder/labels se guide karte hain
        # kaunsa field actually use hoga ye calculation ke waqt method se decide hota hai
        is_aci = "ACI" in method_text
        self.fm_input.setEnabled(is_aci)
        self.zone_combo.setEnabled(not is_aci)

    def build_projects_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search projects...")
        self.search_input.textChanged.connect(self.on_search_changed)
        search_row.addWidget(self.search_input)
        layout.addLayout(search_row)

        self.projects_list = QListWidget()
        layout.addWidget(self.projects_list)

        btn_row = QHBoxLayout()
        self.load_btn = QPushButton("Load Selected")
        self.load_btn.clicked.connect(self.on_load_project)
        btn_row.addWidget(self.load_btn)

        self.delete_btn = QPushButton("Delete Selected")
        self.delete_btn.setObjectName("deleteBtn")
        self.delete_btn.clicked.connect(self.on_delete_project)
        btn_row.addWidget(self.delete_btn)

        layout.addLayout(btn_row)
        return tab

    def make_result_table(self):
        table = QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["Parameter", "Value"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        return table

    def get_current_inputs(self):
        return {
            "method": self.method_combo.currentText(),
            "fck": self.fck_input.text(),
            "slump": self.slump_input.text(),
            "max_agg_size": self.agg_size_combo.currentText(),
            "exposure": self.exposure_combo.currentText(),
            "fm_sand": self.fm_input.text(),
            "zone": self.zone_combo.currentText(),
            "fine_moisture": self.fine_moisture_input.text(),
            "fine_absorption": self.fine_absorption_input.text(),
            "coarse_moisture": self.coarse_moisture_input.text(),
            "coarse_absorption": self.coarse_absorption_input.text(),
            "volume": self.volume_input.text(),
            "bag_weight": self.bag_weight_input.text(),
            "cement_rate": self.cement_rate_input.text(),
            "fine_rate": self.fine_rate_input.text(),
            "coarse_rate": self.coarse_rate_input.text(),
            "water_rate": self.water_rate_input.text(),
        }

    def set_inputs(self, inputs):
        self.method_combo.setCurrentText(inputs.get("method", "ACI 211.1"))
        self.fck_input.setText(str(inputs["fck"]))
        self.slump_input.setText(str(inputs["slump"]))
        self.agg_size_combo.setCurrentText(str(inputs["max_agg_size"]))
        self.exposure_combo.setCurrentText(str(inputs["exposure"]))
        self.fm_input.setText(str(inputs["fm_sand"]))
        self.zone_combo.setCurrentText(str(inputs.get("zone", "II")))
        self.fine_moisture_input.setText(str(inputs["fine_moisture"]))
        self.fine_absorption_input.setText(str(inputs["fine_absorption"]))
        self.coarse_moisture_input.setText(str(inputs["coarse_moisture"]))
        self.coarse_absorption_input.setText(str(inputs["coarse_absorption"]))
        self.volume_input.setText(str(inputs["volume"]))
        self.bag_weight_input.setText(str(inputs["bag_weight"]))
        self.cement_rate_input.setText(str(inputs.get("cement_rate", "0")))
        self.fine_rate_input.setText(str(inputs.get("fine_rate", "0")))
        self.coarse_rate_input.setText(str(inputs.get("coarse_rate", "0")))
        self.water_rate_input.setText(str(inputs.get("water_rate", "0")))

    def on_calculate(self):
        self.error_label.setText("")

        try:
            fck = float(self.fck_input.text())
            slump = float(self.slump_input.text())
            max_agg_size = int(self.agg_size_combo.currentText())
            exposure = self.exposure_combo.currentText()
            fm_sand = float(self.fm_input.text() or 0)
            zone = self.zone_combo.currentText()

            fine_moisture = float(self.fine_moisture_input.text() or 0)
            fine_absorption = float(self.fine_absorption_input.text() or 0)
            coarse_moisture = float(self.coarse_moisture_input.text() or 0)
            coarse_absorption = float(self.coarse_absorption_input.text() or 0)

            volume_m3 = float(self.volume_input.text() or 1)
            bag_weight = float(self.bag_weight_input.text() or 50)

            cement_rate = float(self.cement_rate_input.text() or 0)
            fine_rate = float(self.fine_rate_input.text() or 0)
            coarse_rate = float(self.coarse_rate_input.text() or 0)
            water_rate = float(self.water_rate_input.text() or 0)
        except ValueError:
            self.error_label.setText("Please fill all fields correctly — numeric values only.")
            return

        method = self.method_combo.currentText()

        if "ACI" in method:
            # ACI formally only has 3 exposure categories - map extras down to severe
            aci_exposure = exposure if exposure in ("mild", "moderate", "severe") else "severe"
            result = calculate_mix_aci(
                fck, slump, max_agg_size, aci_exposure, fm_sand,
                fine_moisture, fine_absorption,
                coarse_moisture, coarse_absorption
            )
        else:
            result = calculate_mix_is(
                fck, slump, max_agg_size, exposure, zone,
                fine_moisture, fine_absorption,
                coarse_moisture, coarse_absorption
            )

        self.last_result = result

        batch_info = compute_batch_quantities(result, volume_m3, bag_weight)
        self.last_batch_info = batch_info

        cost_info = compute_cost_estimate(batch_info, cement_rate, fine_rate, coarse_rate, water_rate)
        self.last_cost_info = cost_info

        self.populate_results(result, batch_info, cost_info)

    def on_trial_adjust(self):
        if self.last_result is None:
            QMessageBox.warning(self, "Calculate First", "Please calculate the mix design first.")
            return

        try:
            actual_slump = float(self.actual_slump_input.text())
            target_slump = float(self.slump_input.text())
            adjustment_rate = float(self.water_adj_rate_input.text() or 2.5)
        except ValueError:
            self.error_label.setText("Please enter a valid actual slump value.")
            return

        trial_result = adjust_trial_mix(self.last_result, actual_slump, target_slump, adjustment_rate)
        self.last_trial_result = trial_result

        trial_rows = [
            ("Target Slump", f'{trial_result["target_slump"]} mm'),
            ("Actual Measured Slump", f'{trial_result["actual_slump"]} mm'),
            ("Slump Difference", f'{trial_result["slump_difference"]} mm'),
            ("Water Correction", f'{trial_result["water_correction"]} kg/m³'),
            ("Adjusted Water", f'{trial_result["adjusted_water"]} kg/m³'),
            ("Adjusted Cement", f'{trial_result["adjusted_cement"]} kg/m³'),
            ("Water Change", f'{trial_result["water_change"]} kg/m³'),
            ("Cement Change", f'{trial_result["cement_change"]} kg/m³'),
        ]
        self.fill_table(self.trial_table, trial_rows)
        self.tabs.setCurrentWidget(self.trial_table)

    def populate_results(self, result, batch_info, cost_info):
        common_rows = [
            ("Slump Category", result["slump_category"]),
            ("W/C Ratio (strength-based)", result["wc_strength"]),
            ("W/C Ratio (exposure limit)", result["wc_limit"]),
            ("Final W/C Ratio Used", result["wc_final"]),
            ("Coarse Aggregate Fraction", result["coarse_fraction"]),
            ("Air Content", f'{result["air_percent"]}%'),
        ]

        # IS 10262-only extra info, add karo agar present hai
        if "target_mean_strength" in result:
            common_rows.insert(0, ("Target Mean Strength", f'{result["target_mean_strength"]} MPa'))
        if "min_cement_required" in result:
            common_rows.append(("Minimum Cement Required", f'{result["min_cement_required"]} kg/m³'))

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

        cost_rows = [
            ("Cement Cost", cost_info["cement_cost"]),
            ("Fine Aggregate Cost", cost_info["fine_cost"]),
            ("Coarse Aggregate Cost", cost_info["coarse_cost"]),
            ("Water Cost", cost_info["water_cost"]),
            ("— Total Cost —", cost_info["total_cost"]),
            ("Cost per m³", cost_info["cost_per_m3"]),
        ]

        self.fill_table(self.batch_design_table, batch_rows)
        self.fill_table(self.field_table, field_rows)
        self.fill_table(self.site_batch_table, site_rows)
        self.fill_table(self.cost_table, cost_rows)

        self.trial_table.setRowCount(0)
        self.last_trial_result = None

        try:
            self.charts_widget.update_composition_chart(result)
            self.charts_widget.update_cost_chart(cost_info)
            self.charts_widget.update_batch_vs_field_chart(result)
            self.charts_widget.update_wc_ratio_chart(result)
        except Exception as e:
            QMessageBox.critical(self, "Chart Error", f"Chart update failed:\n{str(e)}")

    def fill_table(self, table, rows):
        table.setRowCount(len(rows))
        for i, (label, value) in enumerate(rows):
            table.setItem(i, 0, QTableWidgetItem(str(label)))
            table.setItem(i, 1, QTableWidgetItem(str(value)))

    def on_save_project(self):
        name = self.project_name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Name Required", "Please enter a project name first.")
            return
        if self.last_result is None:
            QMessageBox.warning(self, "Calculate First", "Please calculate the mix design before saving.")
            return

        inputs = self.get_current_inputs()
        combined_results = {
            "mix": self.last_result,
            "batch": self.last_batch_info,
            "cost": self.last_cost_info,
        }

        save_project(name, inputs, combined_results)
        self.project_name_input.clear()
        self.refresh_projects_list()
        QMessageBox.information(self, "Saved", f"Project '{name}' has been saved successfully.")

    def on_export_pdf(self):
        if self.last_result is None:
            QMessageBox.warning(self, "Calculate First", "Please calculate the mix design before exporting.")
            return

        default_name = self.project_name_input.text().strip() or "mix_design_report"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save PDF Report", f"{default_name}.pdf", "PDF Files (*.pdf)"
        )
        if not file_path:
            return

        inputs = self.get_current_inputs()
        try:
            import tempfile, os
            temp_dir = tempfile.gettempdir()
            pie_path = os.path.join(temp_dir, "mix_pie_chart.png")
            bar_path = os.path.join(temp_dir, "mix_bar_chart.png")
            compare_path = os.path.join(temp_dir, "mix_compare_chart.png")
            wc_path = os.path.join(temp_dir, "mix_wc_chart.png")
            self.charts_widget.save_charts_as_images(pie_path, bar_path, compare_path, wc_path)

            chart_paths = {
                "pie": pie_path,
                "bar": bar_path,
                "compare": compare_path,
                "wc": wc_path,
            }

            generate_pdf_report(
                file_path,
                self.project_name_input.text().strip(),
                inputs,
                self.last_result,
                self.last_batch_info,
                self.last_cost_info,
                chart_image_paths=chart_paths,
                trial_result=self.last_trial_result,
                method_name=inputs["method"]
            )
            QMessageBox.information(self, "Exported", f"PDF report saved to:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Could not generate PDF:\n{str(e)}")

    def refresh_projects_list(self, keyword=None):
        self.projects_list.clear()
        rows = search_projects(keyword) if keyword else get_all_projects()
        for project_id, name, created_at in rows:
            item = QListWidgetItem(f"{name}    ({created_at})")
            item.setData(Qt.UserRole, project_id)
            self.projects_list.addItem(item)

    def on_search_changed(self, text):
        self.refresh_projects_list(keyword=text if text.strip() else None)

    def on_load_project(self):
        selected = self.projects_list.currentItem()
        if not selected:
            QMessageBox.warning(self, "Select a Project", "Please select a project from the list first.")
            return

        project_id = selected.data(Qt.UserRole)
        inputs, results = get_project(project_id)
        if inputs is None:
            QMessageBox.warning(self, "Error", "Failed to load the project.")
            return

        self.set_inputs(inputs)
        self.last_result = results["mix"]
        self.last_batch_info = results["batch"]
        self.last_cost_info = results.get("cost", {
            "cement_cost": 0, "fine_cost": 0, "coarse_cost": 0,
            "water_cost": 0, "total_cost": 0, "cost_per_m3": 0
        })
        self.last_trial_result = None
        self.populate_results(results["mix"], results["batch"], self.last_cost_info)

        QMessageBox.information(self, "Loaded", "Project loaded successfully — view the results in the other tabs.")

    def on_delete_project(self):
        selected = self.projects_list.currentItem()
        if not selected:
            QMessageBox.warning(self, "Select a Project", "Please select a project from the list first.")
            return

        project_id = selected.data(Qt.UserRole)
        confirm = QMessageBox.question(
            self, "Confirm Delete", "Are you sure you want to delete this project?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            delete_project(project_id)
            self.refresh_projects_list()

        def apply_styles(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #1a1f2b;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
                color: #e6e9ef;
            }
            #formScroll {
                border: none;
                background: transparent;
            }
            #card {
                background-color: #242b3a;
                border: 1px solid #313b52;
                border-radius: 14px;
                padding: 24px;
            }
            #title {
                font-size: 21px;
                font-weight: 600;
                color: #ffffff;
                letter-spacing: 0.2px;
            }
            #subtitle {
                font-size: 12px;
                color: #8b94a8;
                margin-bottom: 10px;
            }
            #sectionLabel {
                font-size: 12px;
                font-weight: 600;
                color: #6ea3ff;
                margin-top: 14px;
                letter-spacing: 0.3px;
                text-transform: uppercase;
            }
            QLabel {
                font-size: 13px;
                color: #c4cad6;
                background: transparent;
            }
            QLineEdit {
                background-color: #ffffff;
                border: 1.5px solid #3a4560;
                border-radius: 8px;
                padding: 9px 10px;
                color: #16191f;
                font-size: 13px;
                min-height: 24px;
            }
            QLineEdit:disabled {
                background-color: #cfd3da;
                color: #6b6b6b;
            }
            QLineEdit:focus {
                border: 1.5px solid #4f8cff;
            }
            QComboBox {
                background-color: #ffffff;
                border: 1.5px solid #3a4560;
                border-radius: 8px;
                padding: 9px 10px;
                color: #16191f;
                font-size: 13px;
                min-height: 24px;
            }
            QComboBox:disabled {
                background-color: #cfd3da;
                color: #6b6b6b;
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
                font-weight: 600;
                font-size: 14px;
                padding: 13px;
                border-radius: 10px;
                border: none;
                margin-top: 12px;
            }
            #calcBtn:hover {
                background-color: #3d76e0;
            }
            #calcBtn:pressed {
                background-color: #2e5fc4;
            }
            #trialBtn {
                background-color: #9b59b6;
                color: white;
                font-weight: 600;
                padding: 11px;
                border-radius: 8px;
                border: none;
            }
            #trialBtn:hover {
                background-color: #8e44ad;
            }
            #saveBtn {
                background-color: #2ecc71;
                color: white;
                font-weight: 600;
                padding: 10px 16px;
                border-radius: 8px;
                border: none;
            }
            #saveBtn:hover {
                background-color: #27ae60;
            }
            #pdfBtn {
                background-color: #f39c12;
                color: white;
                font-weight: 600;
                padding: 10px 16px;
                border-radius: 8px;
                border: none;
            }
            #pdfBtn:hover {
                background-color: #d68910;
            }
            #deleteBtn {
                background-color: #e74c3c;
                color: white;
                font-weight: 600;
                padding: 10px 16px;
                border-radius: 8px;
                border: none;
            }
            #deleteBtn:hover {
                background-color: #c0392b;
            }
            #errorLabel {
                color: #ff6b6b;
                font-size: 12px;
                margin-top: 8px;
            }
            QTableWidget, QListWidget {
                background-color: #1a1f2b;
                border: 1px solid #313b52;
                border-radius: 10px;
                gridline-color: #2c3547;
                color: #ffffff;
                selection-background-color: #2e3a52;
            }
            QTableWidget::item, QListWidget::item {
                padding: 6px 4px;
            }
            QHeaderView::section {
                background-color: #2c3547;
                color: #ffffff;
                padding: 8px;
                border: none;
                font-weight: 600;
                font-size: 12px;
            }
            QTabWidget::pane {
                border: none;
                margin-top: 4px;
            }
            QTabBar::tab {
                background-color: #1a1f2b;
                color: #8b94a8;
                padding: 9px 18px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-size: 12px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #4f8cff;
                color: white;
                font-weight: 600;
            }
            QTabBar::tab:hover:!selected {
                background-color: #2c3547;
            }
            QScrollBar:vertical {
                background: #1a1f2b;
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #3a4560;
                border-radius: 5px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: #4f8cff;
            }
        """)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MixDesignApp()
    window.show()
    sys.exit(app.exec())
