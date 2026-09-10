import sys
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QComboBox, QPushButton, QTableWidget,
    QTableWidgetItem, QFrame, QHeaderView, QTabWidget, QListWidget,
    QListWidgetItem, QMessageBox, QScrollArea, QFileDialog, QSplashScreen,
    QStackedWidget, QAbstractItemView
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon, QPixmap, QPainter, QFont, QColor

from logic.mix_design import (
    calculate_mix as calculate_mix_aci,
    compute_batch_quantities, compute_cost_estimate, adjust_trial_mix
)
from logic.is10262 import calculate_mix as calculate_mix_is
from logic.bs_doe import calculate_mix as calculate_mix_bs
from database import (
    init_db, save_project, get_all_projects, get_project, delete_project,
    search_projects, get_project_count, save_setting, get_setting
)
from report_generator import generate_pdf_report
from excel_exporter import export_excel_report
from charts_widget import ChartsWidget
from units import kgm3_to_lbyd3, kg_to_lb, m3_to_yd3


WIZARD_STEP_TITLES = [
    "Step 1 of 3: Design Basics",
    "Step 2 of 3: Site & Moisture",
    "Step 3 of 3: Costs & Review",
]


class MixDesignApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Concrete Mix Design — ACI 211.1 / IS 10262 / BS-DOE")
        self.setWindowIcon(QIcon("app_icon.ico"))
        self.resize(1250, 880)
        self.last_result = None
        self.last_batch_info = None
        self.last_cost_info = None
        self.last_trial_result = None
        self.current_theme = "dark"

        init_db()

        self.build_ui()
        self.apply_styles()
        self.refresh_projects_list()
        self.refresh_dashboard()

    # ================= TOP-LEVEL LAYOUT =================

    def build_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        sidebar = self.build_sidebar()
        main_layout.addWidget(sidebar)

        content_wrapper = QWidget()
        content_layout = QVBoxLayout(content_wrapper)
        content_layout.setContentsMargins(20, 20, 20, 20)

        self.content_stack = QStackedWidget()
        content_layout.addWidget(self.content_stack)

        self.dashboard_page = self.build_dashboard_page()
        self.wizard_page = self.build_wizard_page()
        self.results_page = self.build_results_page()
        self.projects_page = self.build_projects_page()
        self.comparison_page = self.build_comparison_page()
        self.settings_page = self.build_settings_page()

        self.content_stack.addWidget(self.dashboard_page)   # index 0
        self.content_stack.addWidget(self.wizard_page)       # index 1
        self.content_stack.addWidget(self.results_page)      # index 2
        self.content_stack.addWidget(self.projects_page)     # index 3
        self.content_stack.addWidget(self.comparison_page)   # index 4
        self.content_stack.addWidget(self.settings_page)     # index 5

        main_layout.addWidget(content_wrapper, 1)

        self.show_page(0)
        self.on_method_changed(self.method_combo.currentText())

    def build_sidebar(self):
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(160)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(12, 20, 12, 20)
        layout.setSpacing(6)

        logo = QLabel("🧱 Mix Design")
        logo.setObjectName("sidebarLogo")
        layout.addWidget(logo)
        layout.addSpacing(20)

        self.sidebar_buttons = []
        nav_items = [
            ("🏠  Dashboard", 0),
            ("🧮  New Design", 1),
            ("📁  Saved Projects", 3),
            ("⚙️  Settings", 5),
        ]
        for label, page_index in nav_items:
            btn = QPushButton(label)
            btn.setObjectName("sidebarBtn")
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, idx=page_index: self.show_page(idx))
            layout.addWidget(btn)
            self.sidebar_buttons.append((btn, page_index))

        layout.addStretch()

        self.theme_btn = QPushButton("☀️  Light Mode")
        self.theme_btn.setObjectName("themeBtn")
        self.theme_btn.clicked.connect(self.toggle_theme)
        layout.addWidget(self.theme_btn)

        return sidebar

    def show_page(self, index):
        self.content_stack.setCurrentIndex(index)
        for btn, page_index in self.sidebar_buttons:
            btn.setChecked(page_index == index)

    # ================= DASHBOARD PAGE =================

    def build_dashboard_page(self):
        page = QFrame()
        page.setObjectName("card")
        layout = QVBoxLayout(page)
        layout.setSpacing(16)

        welcome = QLabel("Welcome back!")
        welcome.setObjectName("title")
        layout.addWidget(welcome)

        self.dashboard_stats_label = QLabel("")
        self.dashboard_stats_label.setObjectName("subtitle")
        layout.addWidget(self.dashboard_stats_label)

        recent_label = QLabel("RECENT PROJECTS")
        recent_label.setObjectName("sectionLabel")
        layout.addWidget(recent_label)

        self.dashboard_recent_list = QListWidget()
        self.dashboard_recent_list.itemDoubleClicked.connect(self.on_dashboard_load_project)
        layout.addWidget(self.dashboard_recent_list)

        hint = QLabel("Double-click a project to load it instantly.")
        hint.setObjectName("subtitle")
        layout.addWidget(hint)

        new_design_btn = QPushButton("🧮  Start a New Design")
        new_design_btn.setObjectName("calcBtn")
        new_design_btn.clicked.connect(lambda: self.show_page(1))
        layout.addWidget(new_design_btn)

        return page

    def refresh_dashboard(self):
        count = get_project_count()
        self.dashboard_stats_label.setText(f"You have {count} saved project(s).")

        self.dashboard_recent_list.clear()
        recent_rows = get_all_projects()[:5]
        for project_id, name, created_at in recent_rows:
            item = QListWidgetItem(f"{name}    ({created_at})")
            item.setData(Qt.UserRole, project_id)
            self.dashboard_recent_list.addItem(item)

    def on_dashboard_load_project(self, item):
        project_id = item.data(Qt.UserRole)
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
        self.show_page(2)
        self.tabs.setCurrentWidget(self.field_table)

    # ================= WIZARD PAGE (NEW DESIGN) =================

    def build_wizard_page(self):
        page = QFrame()
        page.setObjectName("card")
        layout = QVBoxLayout(page)
        layout.setSpacing(14)

        self.wizard_progress_label = QLabel(WIZARD_STEP_TITLES[0])
        self.wizard_progress_label.setObjectName("title")
        layout.addWidget(self.wizard_progress_label)

        self.method_combo = QComboBox()
        self.method_combo.addItems(["ACI 211.1", "IS 10262", "BS/DOE"])
        self.method_combo.setToolTip(
            "Choose which standard's tables and procedure to use for the mix design calculation."
        )
        self.method_combo.currentTextChanged.connect(self.on_method_changed)

        self.wizard_stack = QStackedWidget()
        layout.addWidget(self.wizard_stack)

        self.wizard_stack.addWidget(self.build_wizard_step1())
        self.wizard_stack.addWidget(self.build_wizard_step2())
        self.wizard_stack.addWidget(self.build_wizard_step3())

        self.error_label = QLabel("")
        self.error_label.setObjectName("errorLabel")
        self.error_label.setWordWrap(True)
        layout.addWidget(self.error_label)

        return page

    def build_wizard_step1(self):
        step = QWidget()
        step_layout = QVBoxLayout(step)
        step_layout.setSpacing(12)

        method_label = QLabel("Design Method")
        method_label.setObjectName("sectionLabel")
        step_layout.addWidget(method_label)
        step_layout.addWidget(self.method_combo)

        grid = QGridLayout()
        grid.setVerticalSpacing(12)
        grid.setHorizontalSpacing(10)

        grid.addWidget(QLabel("Target Strength f'ck (MPa)"), 0, 0)
        self.fck_input = QLineEdit()
        self.fck_input.setPlaceholderText("e.g. 30")
        grid.addWidget(self.fck_input, 0, 1)
        self.fck_input.setToolTip(
            "Target compressive strength of concrete (f'ck) in MPa.\n"
            "This is the design strength specified by the structural engineer,\n"
            "e.g. M25 concrete = 25 MPa."
        )

        grid.addWidget(QLabel("Slump (mm)"), 1, 0)
        self.slump_input = QLineEdit()
        self.slump_input.setPlaceholderText("e.g. 100")
        grid.addWidget(self.slump_input, 1, 1)
        self.slump_input.setToolTip(
            "Desired workability of fresh concrete, measured by the slump test (mm).\n"
            "Higher slump = more flowable mix. Typical range: 25-150mm."
        )

        grid.addWidget(QLabel("Max Aggregate Size (mm)"), 2, 0)
        self.agg_size_combo = QComboBox()
        self.agg_size_combo.addItems(["10", "20", "40"])
        self.agg_size_combo.setCurrentText("20")
        grid.addWidget(self.agg_size_combo, 2, 1)
        self.agg_size_combo.setToolTip(
            "Maximum nominal size of coarse aggregate (mm) used in the mix.\n"
            "Larger aggregate generally needs less cement paste."
        )

        grid.addWidget(QLabel("Exposure Condition"), 3, 0)
        self.exposure_combo = QComboBox()
        self.exposure_combo.addItems(["mild", "moderate", "severe", "very_severe", "extreme"])
        grid.addWidget(self.exposure_combo, 3, 1)
        self.exposure_combo.setToolTip(
            "Environmental exposure condition of the structure.\n"
            "Determines durability requirements (max w/c ratio, min cement, air content)."
        )

        grid.addWidget(QLabel("Fineness Modulus of Sand (ACI)"), 4, 0)
        self.fm_input = QLineEdit()
        self.fm_input.setPlaceholderText("e.g. 2.6")
        grid.addWidget(self.fm_input, 4, 1)
        self.fm_input.setToolTip(
            "Fineness Modulus of sand. Typical range: 2.3 to 3.1. Used only for ACI 211.1."
        )

        grid.addWidget(QLabel("Sand Zone (IS 10262 / BS-DOE)"), 5, 0)
        self.zone_combo = QComboBox()
        self.zone_combo.addItems(["I", "II", "III", "IV"])
        self.zone_combo.setCurrentText("II")
        grid.addWidget(self.zone_combo, 5, 1)
        self.zone_combo.setToolTip(
            "Grading zone of fine aggregate as per IS 383. Used for IS 10262 and BS/DOE."
        )

        grid.addWidget(QLabel("Aggregate Type (BS/DOE)"), 6, 0)
        self.aggregate_type_combo = QComboBox()
        self.aggregate_type_combo.addItems(["uncrushed", "crushed"])
        grid.addWidget(self.aggregate_type_combo, 6, 1)
        self.aggregate_type_combo.setToolTip(
            "Shape of coarse aggregate — crushed needs more water than uncrushed. Used only for BS/DOE."
        )

        step_layout.addLayout(grid)
        step_layout.addStretch()

        nav_row = QHBoxLayout()
        nav_row.addStretch()
        next_btn = QPushButton("Next →")
        next_btn.setObjectName("wizardNavBtn")
        next_btn.clicked.connect(self.next_step)
        nav_row.addWidget(next_btn)
        step_layout.addLayout(nav_row)

        return step

    def build_wizard_step2(self):
        step = QWidget()
        step_layout = QVBoxLayout(step)
        step_layout.setSpacing(12)

        moisture_label = QLabel("Aggregate Moisture Correction (optional, defaults to 0)")
        moisture_label.setObjectName("sectionLabel")
        step_layout.addWidget(moisture_label)

        moisture_grid = QGridLayout()
        moisture_grid.setVerticalSpacing(12)
        moisture_grid.setHorizontalSpacing(10)

        moisture_grid.addWidget(QLabel("Fine Agg. Moisture (%)"), 0, 0)
        self.fine_moisture_input = QLineEdit("0")
        moisture_grid.addWidget(self.fine_moisture_input, 0, 1)
        self.fine_moisture_input.setToolTip(
            "Total moisture content currently present in the fine aggregate (%), measured on site."
        )

        moisture_grid.addWidget(QLabel("Fine Agg. Absorption (%)"), 1, 0)
        self.fine_absorption_input = QLineEdit("0")
        moisture_grid.addWidget(self.fine_absorption_input, 1, 1)
        self.fine_absorption_input.setToolTip(
            "Water absorption capacity of the fine aggregate (%)."
        )

        moisture_grid.addWidget(QLabel("Coarse Agg. Moisture (%)"), 2, 0)
        self.coarse_moisture_input = QLineEdit("0")
        moisture_grid.addWidget(self.coarse_moisture_input, 2, 1)
        self.coarse_moisture_input.setToolTip(
            "Total moisture content currently present in the coarse aggregate (%), measured on site."
        )

        moisture_grid.addWidget(QLabel("Coarse Agg. Absorption (%)"), 3, 0)
        self.coarse_absorption_input = QLineEdit("0")
        moisture_grid.addWidget(self.coarse_absorption_input, 3, 1)
        self.coarse_absorption_input.setToolTip(
            "Water absorption capacity of the coarse aggregate (%)."
        )

        step_layout.addLayout(moisture_grid)

        admixture_label = QLabel("Admixture (Optional)")
        admixture_label.setObjectName("sectionLabel")
        step_layout.addWidget(admixture_label)

        admixture_grid = QGridLayout()
        admixture_grid.addWidget(QLabel("Water Reduction (%)"), 0, 0)
        self.admixture_input = QLineEdit("0")
        admixture_grid.addWidget(self.admixture_input, 0, 1)
        self.admixture_input.setToolTip(
            "If using a superplasticizer or water-reducing admixture, enter the percentage\n"
            "by which it reduces water demand (typically 5-25% depending on dosage and type).\n"
            "Leave at 0 if not using any admixture."
        )
        step_layout.addLayout(admixture_grid)

        batch_label = QLabel("Batch / Site Quantity")
        batch_label.setObjectName("sectionLabel")
        step_layout.addWidget(batch_label)

        batch_grid = QGridLayout()
        batch_grid.setVerticalSpacing(12)
        batch_grid.setHorizontalSpacing(10)

        batch_grid.addWidget(QLabel("Total Volume Needed (m³)"), 0, 0)
        self.volume_input = QLineEdit("1")
        batch_grid.addWidget(self.volume_input, 0, 1)
        self.volume_input.setToolTip(
            "Total volume of concrete (in m³) you need to produce for this pour/project."
        )

        batch_grid.addWidget(QLabel("Cement Bag Weight (kg)"), 1, 0)
        self.bag_weight_input = QLineEdit("50")
        batch_grid.addWidget(self.bag_weight_input, 1, 1)
        self.bag_weight_input.setToolTip(
            "Standard weight of one cement bag (kg). Commonly 50kg."
        )

        step_layout.addLayout(batch_grid)
        step_layout.addStretch()

        nav_row = QHBoxLayout()
        back_btn = QPushButton("← Back")
        back_btn.setObjectName("wizardNavBtn")
        back_btn.clicked.connect(self.prev_step)
        nav_row.addWidget(back_btn)
        nav_row.addStretch()
        next_btn = QPushButton("Next →")
        next_btn.setObjectName("wizardNavBtn")
        next_btn.clicked.connect(self.next_step)
        nav_row.addWidget(next_btn)
        step_layout.addLayout(nav_row)

        return step

    def build_wizard_step3(self):
        step = QWidget()
        step_layout = QVBoxLayout(step)
        step_layout.setSpacing(12)

        cost_label = QLabel("Material Rates (for cost estimation)")
        cost_label.setObjectName("sectionLabel")
        step_layout.addWidget(cost_label)

        cost_grid = QGridLayout()
        cost_grid.setVerticalSpacing(12)
        cost_grid.setHorizontalSpacing(10)

        cost_grid.addWidget(QLabel("Cement Rate (per bag)"), 0, 0)
        self.cement_rate_input = QLineEdit("0")
        cost_grid.addWidget(self.cement_rate_input, 0, 1)
        self.cement_rate_input.setToolTip("Cost of one bag of cement in your local currency.")

        cost_grid.addWidget(QLabel("Fine Aggregate Rate (per kg)"), 1, 0)
        self.fine_rate_input = QLineEdit("0")
        cost_grid.addWidget(self.fine_rate_input, 1, 1)
        self.fine_rate_input.setToolTip("Cost per kg of fine aggregate (sand).")

        cost_grid.addWidget(QLabel("Coarse Aggregate Rate (per kg)"), 2, 0)
        self.coarse_rate_input = QLineEdit("0")
        cost_grid.addWidget(self.coarse_rate_input, 2, 1)
        self.coarse_rate_input.setToolTip("Cost per kg of coarse aggregate.")

        cost_grid.addWidget(QLabel("Water Rate (per liter, optional)"), 3, 0)
        self.water_rate_input = QLineEdit("0")
        cost_grid.addWidget(self.water_rate_input, 3, 1)
        self.water_rate_input.setToolTip("Cost per liter of water, if applicable.")

        step_layout.addLayout(cost_grid)

        save_label = QLabel("Project Name (for saving / report)")
        save_label.setObjectName("sectionLabel")
        step_layout.addWidget(save_label)

        self.project_name_input = QLineEdit()
        self.project_name_input.setPlaceholderText("e.g. Site A - Column Mix")
        step_layout.addWidget(self.project_name_input)

        step_layout.addStretch()

        nav_row = QHBoxLayout()
        back_btn = QPushButton("← Back")
        back_btn.setObjectName("wizardNavBtn")
        back_btn.clicked.connect(self.prev_step)
        nav_row.addWidget(back_btn)
        nav_row.addStretch()

        self.calc_btn = QPushButton("🧮  Calculate Mix Design")
        self.calc_btn.setObjectName("calcBtn")
        self.calc_btn.clicked.connect(self.on_calculate)
        nav_row.addWidget(self.calc_btn)

        step_layout.addLayout(nav_row)

        return step

    def next_step(self):
        idx = self.wizard_stack.currentIndex()
        if idx < 2:
            self.wizard_stack.setCurrentIndex(idx + 1)
            self.wizard_progress_label.setText(WIZARD_STEP_TITLES[idx + 1])

    def prev_step(self):
        idx = self.wizard_stack.currentIndex()
        if idx > 0:
            self.wizard_stack.setCurrentIndex(idx - 1)
            self.wizard_progress_label.setText(WIZARD_STEP_TITLES[idx - 1])

    def on_method_changed(self, method_text):
        is_aci = "ACI" in method_text
        is_bs = "BS" in method_text
        is_is = ("IS" in method_text) and not is_bs

        self.fm_input.setEnabled(is_aci)
        self.zone_combo.setEnabled(is_is or is_bs)
        self.aggregate_type_combo.setEnabled(is_bs)

    # ================= RESULTS PAGE =================

    def build_results_page(self):
        page = QFrame()
        page.setObjectName("card")
        layout = QVBoxLayout(page)
        layout.setSpacing(14)

        top_row = QHBoxLayout()
        result_title = QLabel("Mix Design Results")
        result_title.setObjectName("title")
        top_row.addWidget(result_title)
        top_row.addStretch()

        edit_btn = QPushButton("✏️  Edit Inputs")
        edit_btn.setObjectName("wizardNavBtn")
        edit_btn.clicked.connect(lambda: self.show_page(1))
        top_row.addWidget(edit_btn)

        self.save_btn = QPushButton("💾  Save Project")
        self.save_btn.setObjectName("saveBtn")
        self.save_btn.clicked.connect(self.on_save_project)
        top_row.addWidget(self.save_btn)

        self.pdf_btn = QPushButton("📄  Export PDF")
        self.pdf_btn.setObjectName("pdfBtn")
        self.pdf_btn.clicked.connect(self.on_export_pdf)
        top_row.addWidget(self.pdf_btn)

        self.excel_btn = QPushButton("📊  Export Excel")
        self.excel_btn.setObjectName("excelBtn")
        self.excel_btn.clicked.connect(self.on_export_excel)
        top_row.addWidget(self.excel_btn)

        layout.addLayout(top_row)

        self.tabs = QTabWidget()

        self.batch_design_table = self.make_result_table()
        self.field_table = self.make_result_table()
        self.site_batch_table = self.make_result_table()
        self.cost_table = self.make_result_table()
        self.trial_tab = self.build_trial_tab()
        self.charts_widget = ChartsWidget()

        self.tabs.addTab(self.batch_design_table, "Batch (Dry) Quantities")
        self.tabs.addTab(self.field_table, "Field (Moisture Adjusted)")
        self.tabs.addTab(self.site_batch_table, "Site Batching")
        self.tabs.addTab(self.cost_table, "Cost Estimation")
        self.tabs.addTab(self.trial_tab, "Trial Mix Adjustment")
        self.tabs.addTab(self.charts_widget, "Charts")

        layout.addWidget(self.tabs)

        return page

    def build_trial_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)

        form_row = QGridLayout()
        form_row.addWidget(QLabel("Actual Measured Slump (mm)"), 0, 0)
        self.actual_slump_input = QLineEdit()
        self.actual_slump_input.setPlaceholderText("e.g. 80")
        form_row.addWidget(self.actual_slump_input, 0, 1)
        self.actual_slump_input.setToolTip(
            "The slump you actually measured after casting a trial batch on site."
        )

        form_row.addWidget(QLabel("Water Adjustment Rate (kg per 10mm)"), 1, 0)
        self.water_adj_rate_input = QLineEdit("2.5")
        form_row.addWidget(self.water_adj_rate_input, 1, 1)
        self.water_adj_rate_input.setToolTip(
            "How much water (kg/m³) to add or remove per 10mm difference between\n"
            "actual and target slump. Typical value: 2-3 kg per 10mm."
        )
        layout.addLayout(form_row)

        self.trial_btn = QPushButton("🔧  Compute Trial Adjustment")
        self.trial_btn.setObjectName("trialBtn")
        self.trial_btn.clicked.connect(self.on_trial_adjust)
        layout.addWidget(self.trial_btn)

        self.trial_table = self.make_result_table()
        layout.addWidget(self.trial_table)

        return tab

    def make_result_table(self):
        table = QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["Parameter", "Value"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        return table

    # ================= SAVED PROJECTS PAGE =================

    def build_projects_page(self):
        page = QFrame()
        page.setObjectName("card")
        layout = QVBoxLayout(page)
        layout.setSpacing(14)

        title = QLabel("Saved Projects")
        title.setObjectName("title")
        layout.addWidget(title)

        hint = QLabel("Select 2-3 projects (Ctrl+Click) to compare them side by side.")
        hint.setObjectName("subtitle")
        layout.addWidget(hint)

        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search projects...")
        self.search_input.textChanged.connect(self.on_search_changed)
        search_row.addWidget(self.search_input)
        layout.addLayout(search_row)

        self.projects_list = QListWidget()
        self.projects_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        layout.addWidget(self.projects_list)

        btn_row = QHBoxLayout()
        self.load_btn = QPushButton("Load Selected")
        self.load_btn.clicked.connect(self.on_load_project)
        btn_row.addWidget(self.load_btn)

        self.compare_btn = QPushButton("⚖️  Compare Selected")
        self.compare_btn.setObjectName("wizardNavBtn")
        self.compare_btn.clicked.connect(self.on_compare_projects)
        btn_row.addWidget(self.compare_btn)

        self.delete_btn = QPushButton("Delete Selected")
        self.delete_btn.setObjectName("deleteBtn")
        self.delete_btn.clicked.connect(self.on_delete_project)
        btn_row.addWidget(self.delete_btn)

        layout.addLayout(btn_row)
        return page

    # ================= COMPARISON PAGE =================

    def build_comparison_page(self):
        page = QFrame()
        page.setObjectName("card")
        layout = QVBoxLayout(page)
        layout.setSpacing(14)

        top_row = QHBoxLayout()
        title = QLabel("Project Comparison")
        title.setObjectName("title")
        top_row.addWidget(title)
        top_row.addStretch()

        back_btn = QPushButton("← Back to Saved Projects")
        back_btn.setObjectName("wizardNavBtn")
        back_btn.clicked.connect(lambda: self.show_page(3))
        top_row.addWidget(back_btn)
        layout.addLayout(top_row)

        self.comparison_table = QTableWidget()
        self.comparison_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.comparison_table.verticalHeader().setVisible(False)
        self.comparison_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.comparison_table)

        return page

    def on_compare_projects(self):
        selected_items = self.projects_list.selectedItems()

        if len(selected_items) < 2:
            QMessageBox.warning(self, "Select More Projects", "Please select at least 2 projects to compare (Ctrl+Click).")
            return
        if len(selected_items) > 3:
            QMessageBox.warning(self, "Too Many Selected", "Please select a maximum of 3 projects to compare.")
            return

        project_names = []
        project_data = []

        for item in selected_items:
            project_id = item.data(Qt.UserRole)
            inputs, results = get_project(project_id)
            if inputs is None:
                continue
            project_names.append(inputs.get("method", "") + " — " + item.text().split("    (")[0])
            project_data.append((inputs, results))

        metric_rows = [
            ("Design Method", lambda i, r: i.get("method", "")),
            ("Target Strength (f'ck)", lambda i, r: f"{i.get('fck', '')} MPa"),
            ("Slump", lambda i, r: f"{i.get('slump', '')} mm"),
            ("Exposure Condition", lambda i, r: i.get("exposure", "").replace("_", " ").capitalize()),
            ("Final W/C Ratio", lambda i, r: r["mix"]["wc_final"]),
            ("Cement (field, kg/m³)", lambda i, r: r["mix"]["cement_field"]),
            ("Water (field, kg/m³)", lambda i, r: r["mix"]["water_field"]),
            ("Fine Aggregate (field, kg/m³)", lambda i, r: r["mix"]["fine_field"]),
            ("Coarse Aggregate (field, kg/m³)", lambda i, r: r["mix"]["coarse_field"]),
            ("Total Cement Bags", lambda i, r: r["batch"]["total_bags"]),
            ("Total Cost", lambda i, r: r.get("cost", {}).get("total_cost", "N/A")),
            ("Cost per m³", lambda i, r: r.get("cost", {}).get("cost_per_m3", "N/A")),
        ]

        self.comparison_table.setColumnCount(len(project_names) + 1)
        self.comparison_table.setHorizontalHeaderLabels(["Metric"] + project_names)
        self.comparison_table.setRowCount(len(metric_rows))

        for row_idx, (label, extractor) in enumerate(metric_rows):
            self.comparison_table.setItem(row_idx, 0, QTableWidgetItem(label))
            for col_idx, (inputs, results) in enumerate(project_data):
                try:
                    value = extractor(inputs, results)
                except Exception:
                    value = "N/A"
                self.comparison_table.setItem(row_idx, col_idx + 1, QTableWidgetItem(str(value)))

        self.show_page(4)

    # ================= SETTINGS PAGE =================

    def build_settings_page(self):
        page = QFrame()
        page.setObjectName("card")
        layout = QVBoxLayout(page)
        layout.setSpacing(14)

        title = QLabel("Settings")
        title.setObjectName("title")
        layout.addWidget(title)

        branding_label = QLabel("Report Branding (optional)")
        branding_label.setObjectName("sectionLabel")
        layout.addWidget(branding_label)

        hint = QLabel("If set, this appears as a letterhead at the top of every PDF and Excel report.")
        hint.setObjectName("subtitle")
        layout.addWidget(hint)

        grid = QGridLayout()
        grid.addWidget(QLabel("Company / Firm Name"), 0, 0)
        self.company_name_input = QLineEdit()
        self.company_name_input.setPlaceholderText("e.g. ABC Consulting Engineers")
        grid.addWidget(self.company_name_input, 0, 1)

        grid.addWidget(QLabel("Address / Contact Line"), 1, 0)
        self.company_address_input = QLineEdit()
        self.company_address_input.setPlaceholderText("e.g. Lahore, Pakistan | +92-xxx-xxxxxxx")
        grid.addWidget(self.company_address_input, 1, 1)

        layout.addLayout(grid)

        units_label = QLabel("Unit System")
        units_label.setObjectName("sectionLabel")
        layout.addWidget(units_label)

        self.unit_system_combo = QComboBox()
        self.unit_system_combo.addItems(["Metric (kg, m³)", "Imperial (lb, yd³)"])
        self.unit_system_combo.setToolTip(
            "Choose how quantities are displayed in the results tables.\n"
            "All calculations are always done in metric internally; this only affects display."
        )
        layout.addWidget(self.unit_system_combo)

        save_settings_btn = QPushButton("💾  Save Settings")
        save_settings_btn.setObjectName("saveBtn")
        save_settings_btn.clicked.connect(self.on_save_settings)
        layout.addWidget(save_settings_btn)

        layout.addStretch()

        self.company_name_input.setText(get_setting("company_name", ""))
        self.company_address_input.setText(get_setting("company_address", ""))
        saved_unit = get_setting("unit_system", "metric")
        self.unit_system_combo.setCurrentText(
            "Imperial (lb, yd³)" if saved_unit == "imperial" else "Metric (kg, m³)"
        )

        return page

    def on_save_settings(self):
        save_setting("company_name", self.company_name_input.text().strip())
        save_setting("company_address", self.company_address_input.text().strip())

        unit_system = "imperial" if "Imperial" in self.unit_system_combo.currentText() else "metric"
        save_setting("unit_system", unit_system)

        QMessageBox.information(self, "Saved", "Settings have been saved.")

    # ================= DATA / INPUT HELPERS =================

    def get_current_inputs(self):
        return {
            "method": self.method_combo.currentText(),
            "fck": self.fck_input.text(),
            "slump": self.slump_input.text(),
            "max_agg_size": self.agg_size_combo.currentText(),
            "exposure": self.exposure_combo.currentText(),
            "fm_sand": self.fm_input.text(),
            "zone": self.zone_combo.currentText(),
            "aggregate_type": self.aggregate_type_combo.currentText(),
            "fine_moisture": self.fine_moisture_input.text(),
            "fine_absorption": self.fine_absorption_input.text(),
            "coarse_moisture": self.coarse_moisture_input.text(),
            "coarse_absorption": self.coarse_absorption_input.text(),
            "admixture_reduction": self.admixture_input.text(),
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
        self.aggregate_type_combo.setCurrentText(str(inputs.get("aggregate_type", "uncrushed")))
        self.fine_moisture_input.setText(str(inputs["fine_moisture"]))
        self.fine_absorption_input.setText(str(inputs["fine_absorption"]))
        self.coarse_moisture_input.setText(str(inputs["coarse_moisture"]))
        self.coarse_absorption_input.setText(str(inputs["coarse_absorption"]))
        self.admixture_input.setText(str(inputs.get("admixture_reduction", "0")))
        self.volume_input.setText(str(inputs["volume"]))
        self.bag_weight_input.setText(str(inputs["bag_weight"]))
        self.cement_rate_input.setText(str(inputs.get("cement_rate", "0")))
        self.fine_rate_input.setText(str(inputs.get("fine_rate", "0")))
        self.coarse_rate_input.setText(str(inputs.get("coarse_rate", "0")))
        self.water_rate_input.setText(str(inputs.get("water_rate", "0")))

    # ================= CALCULATE / RESULTS =================

    def on_calculate(self):
        self.error_label.setText("")
        self.calc_btn.setEnabled(False)
        self.calc_btn.setText("⏳  Calculating...")
        QApplication.processEvents()

        try:
            fck = float(self.fck_input.text())
            slump = float(self.slump_input.text())
            max_agg_size = int(self.agg_size_combo.currentText())
            exposure = self.exposure_combo.currentText()
            fm_sand = float(self.fm_input.text() or 0)
            zone = self.zone_combo.currentText()
            aggregate_type = self.aggregate_type_combo.currentText()

            fine_moisture = float(self.fine_moisture_input.text() or 0)
            fine_absorption = float(self.fine_absorption_input.text() or 0)
            coarse_moisture = float(self.coarse_moisture_input.text() or 0)
            coarse_absorption = float(self.coarse_absorption_input.text() or 0)
            admixture_reduction = float(self.admixture_input.text() or 0)

            volume_m3 = float(self.volume_input.text() or 1)
            bag_weight = float(self.bag_weight_input.text() or 50)

            cement_rate = float(self.cement_rate_input.text() or 0)
            fine_rate = float(self.fine_rate_input.text() or 0)
            coarse_rate = float(self.coarse_rate_input.text() or 0)
            water_rate = float(self.water_rate_input.text() or 0)
        except ValueError:
            self.error_label.setText("Please fill all fields correctly — numeric values only.")
            self.calc_btn.setEnabled(True)
            self.calc_btn.setText("🧮  Calculate Mix Design")
            return

        method = self.method_combo.currentText()

        if "ACI" in method:
            aci_exposure = exposure if exposure in ("mild", "moderate", "severe") else "severe"
            result = calculate_mix_aci(
                fck, slump, max_agg_size, aci_exposure, fm_sand,
                fine_moisture, fine_absorption,
                coarse_moisture, coarse_absorption,
                admixture_reduction
            )
        elif "BS" in method:
            result = calculate_mix_bs(
                fck, slump, max_agg_size, exposure, zone, aggregate_type,
                fine_moisture, fine_absorption,
                coarse_moisture, coarse_absorption,
                admixture_reduction
            )
        else:
            result = calculate_mix_is(
                fck, slump, max_agg_size, exposure, zone,
                fine_moisture, fine_absorption,
                coarse_moisture, coarse_absorption,
                admixture_reduction
            )

        self.last_result = result

        batch_info = compute_batch_quantities(result, volume_m3, bag_weight)
        self.last_batch_info = batch_info

        cost_info = compute_cost_estimate(batch_info, cement_rate, fine_rate, coarse_rate, water_rate)
        self.last_cost_info = cost_info

        self.populate_results(result, batch_info, cost_info)

        self.calc_btn.setEnabled(True)
        self.calc_btn.setText("🧮  Calculate Mix Design")

        self.show_page(2)
        self.tabs.setCurrentIndex(0)

    def on_trial_adjust(self):
        if self.last_result is None:
            QMessageBox.warning(self, "Calculate First", "Please calculate the mix design first.")
            return

        try:
            actual_slump = float(self.actual_slump_input.text())
            target_slump = float(self.slump_input.text())
            adjustment_rate = float(self.water_adj_rate_input.text() or 2.5)
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Please enter a valid actual slump value.")
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

    def populate_results(self, result, batch_info, cost_info):
        unit_system = get_setting("unit_system", "metric")
        is_imperial = (unit_system == "imperial")

        def qty_label(value):
            if is_imperial:
                return f"{kgm3_to_lbyd3(value):.1f} lb/yd³"
            return f"{value} kg/m³"

        def mass_label(value):
            if is_imperial:
                return f"{kg_to_lb(value):.1f} lb"
            return f"{value} kg"

        def volume_label(value):
            if is_imperial:
                return f"{m3_to_yd3(value):.2f} yd³"
            return f"{value} m³"

        common_rows = [
            ("Slump Category", result["slump_category"]),
            ("W/C Ratio (strength-based)", result["wc_strength"]),
            ("W/C Ratio (exposure limit)", result["wc_limit"]),
            ("Final W/C Ratio Used", result["wc_final"]),
            ("Coarse Aggregate Fraction", result["coarse_fraction"]),
            ("Air Content", f'{result["air_percent"]}%'),
        ]

        if "target_mean_strength" in result:
            common_rows.insert(0, ("Target Mean Strength", f'{result["target_mean_strength"]} MPa'))
        if "min_cement_required" in result:
            common_rows.append(("Minimum Cement Required", qty_label(result["min_cement_required"])))

        batch_rows = common_rows + [
            ("Water (batch)", qty_label(result["water_batch"])),
            ("Cement (batch)", qty_label(result["cement_batch"])),
            ("Fine Aggregate (batch)", qty_label(result["fine_batch"])),
            ("Coarse Aggregate (batch)", qty_label(result["coarse_batch"])),
        ]

        field_rows = common_rows + [
            ("Water (field, adjusted)", qty_label(result["water_field"])),
            ("Cement (field)", qty_label(result["cement_field"])),
            ("Fine Aggregate (field)", qty_label(result["fine_field"])),
            ("Coarse Aggregate (field)", qty_label(result["coarse_field"])),
        ]

        site_rows = [
            ("Cement Bags per m³", batch_info["bags_per_m3"]),
            ("Water per Bag", mass_label(batch_info["water_per_bag"])),
            ("Fine Aggregate per Bag", mass_label(batch_info["fine_per_bag"])),
            ("Coarse Aggregate per Bag", mass_label(batch_info["coarse_per_bag"])),
            ("— Total for Requested Volume —", volume_label(batch_info["volume_m3"])),
            ("Total Cement Bags", batch_info["total_bags"]),
            ("Total Cement", mass_label(batch_info["total_cement_kg"])),
            ("Total Water", mass_label(batch_info["total_water_kg"])),
            ("Total Fine Aggregate", mass_label(batch_info["total_fine_kg"])),
            ("Total Coarse Aggregate", mass_label(batch_info["total_coarse_kg"])),
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

    # ================= SAVE / EXPORT =================

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
        self.refresh_dashboard()
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

        self.pdf_btn.setEnabled(False)
        self.pdf_btn.setText("⏳  Generating...")
        QApplication.processEvents()

        try:
            import tempfile, os
            temp_dir = tempfile.gettempdir()
            pie_path = os.path.join(temp_dir, "mix_pie_chart.png")
            bar_path = os.path.join(temp_dir, "mix_bar_chart.png")
            compare_path = os.path.join(temp_dir, "mix_compare_chart.png")
            wc_path = os.path.join(temp_dir, "mix_wc_chart.png")
            self.charts_widget.save_charts_as_images(pie_path, bar_path, compare_path, wc_path)

            chart_paths = {"pie": pie_path, "bar": bar_path, "compare": compare_path, "wc": wc_path}

            generate_pdf_report(
                file_path,
                self.project_name_input.text().strip(),
                inputs,
                self.last_result,
                self.last_batch_info,
                self.last_cost_info,
                chart_image_paths=chart_paths,
                trial_result=self.last_trial_result,
                method_name=inputs["method"],
                company_name=get_setting("company_name", ""),
                company_address=get_setting("company_address", "")
            )
            QMessageBox.information(self, "Exported", f"PDF report saved to:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Could not generate PDF:\n{str(e)}")
        finally:
            self.pdf_btn.setEnabled(True)
            self.pdf_btn.setText("📄  Export PDF")

    def on_export_excel(self):
        if self.last_result is None:
            QMessageBox.warning(self, "Calculate First", "Please calculate the mix design before exporting.")
            return

        default_name = self.project_name_input.text().strip() or "mix_design_report"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Excel Report", f"{default_name}.xlsx", "Excel Files (*.xlsx)"
        )
        if not file_path:
            return

        inputs = self.get_current_inputs()

        self.excel_btn.setEnabled(False)
        self.excel_btn.setText("⏳  Generating...")
        QApplication.processEvents()

        try:
            export_excel_report(
                file_path,
                self.project_name_input.text().strip(),
                inputs,
                self.last_result,
                self.last_batch_info,
                self.last_cost_info,
                trial_result=self.last_trial_result,
                method_name=inputs["method"],
                company_name=get_setting("company_name", ""),
                company_address=get_setting("company_address", "")
            )
            QMessageBox.information(self, "Exported", f"Excel report saved to:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Could not generate Excel file:\n{str(e)}")
        finally:
            self.excel_btn.setEnabled(True)
            self.excel_btn.setText("📊  Export Excel")

    # ================= SAVED PROJECTS =================

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
        self.show_page(2)
        self.tabs.setCurrentWidget(self.field_table)

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
            self.refresh_dashboard()

    # ================= STYLING =================

    def apply_styles(self):
        self.setStyleSheet(self.get_theme_stylesheet(self.current_theme))

    def get_theme_stylesheet(self, theme):
        if theme == "light":
            bg_main = "#f4f6fa"
            bg_card = "#ffffff"
            bg_sidebar = "#eef1f7"
            border_color = "#d8dde6"
            text_main = "#1e2530"
            text_muted = "#6b7280"
            input_bg = "#ffffff"
            input_text = "#16191f"
            table_bg = "#ffffff"
            table_text = "#1e2530"
            tab_bg = "#e9ecf3"
        else:
            bg_main = "#1a1f2b"
            bg_card = "#242b3a"
            bg_sidebar = "#161b26"
            border_color = "#313b52"
            text_main = "#e6e9ef"
            text_muted = "#8b94a8"
            input_bg = "#ffffff"
            input_text = "#16191f"
            table_bg = "#1a1f2b"
            table_text = "#ffffff"
            tab_bg = "#1a1f2b"

        return f"""
            QWidget {{
                background-color: {bg_main};
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
                color: {text_main};
            }}
            #sidebar {{
                background-color: {bg_sidebar};
                border-right: 1px solid {border_color};
            }}
            #sidebarLogo {{
                font-size: 15px;
                font-weight: 700;
                color: {text_main};
            }}
            #sidebarBtn {{
                background-color: transparent;
                color: {text_muted};
                border: none;
                border-radius: 8px;
                padding: 10px 12px;
                text-align: left;
                font-size: 13px;
                font-weight: 600;
            }}
            #sidebarBtn:hover {{
                background-color: {border_color};
            }}
            #sidebarBtn:checked {{
                background-color: #4f8cff;
                color: white;
            }}
            #card {{
                background-color: {bg_card};
                border: 1px solid {border_color};
                border-radius: 14px;
                padding: 24px;
            }}
            #title {{
                font-size: 21px;
                font-weight: 600;
                color: {text_main};
                letter-spacing: 0.2px;
            }}
            #subtitle {{
                font-size: 12px;
                color: {text_muted};
                margin-bottom: 10px;
            }}
            #sectionLabel {{
                font-size: 12px;
                font-weight: 600;
                color: #4f8cff;
                margin-top: 14px;
                letter-spacing: 0.3px;
                text-transform: uppercase;
            }}
            QLabel {{
                font-size: 13px;
                color: {text_main};
                background: transparent;
            }}
            QLineEdit {{
                background-color: {input_bg};
                border: 1.5px solid {border_color};
                border-radius: 8px;
                padding: 9px 10px;
                color: {input_text};
                font-size: 13px;
                min-height: 24px;
            }}
            QLineEdit:disabled {{
                background-color: #cfd3da;
                color: #6b6b6b;
            }}
            QLineEdit:focus {{
                border: 1.5px solid #4f8cff;
            }}
            QComboBox {{
                background-color: {input_bg};
                border: 1.5px solid {border_color};
                border-radius: 8px;
                padding: 9px 10px;
                color: {input_text};
                font-size: 13px;
                min-height: 24px;
            }}
            QComboBox:disabled {{
                background-color: #cfd3da;
                color: #6b6b6b;
            }}
            QComboBox QAbstractItemView {{
                background-color: #ffffff;
                color: #000000;
                selection-background-color: #4f8cff;
                selection-color: #ffffff;
            }}
            #calcBtn {{
                background-color: #4f8cff;
                color: white;
                font-weight: 600;
                font-size: 14px;
                padding: 13px;
                border-radius: 10px;
                border: none;
            }}
            #calcBtn:hover {{
                background-color: #3d76e0;
            }}
            #wizardNavBtn {{
                background-color: {bg_card};
                color: {text_main};
                border: 1.5px solid {border_color};
                font-weight: 600;
                padding: 10px 18px;
                border-radius: 8px;
            }}
            #wizardNavBtn:hover {{
                background-color: {border_color};
            }}
            #trialBtn {{
                background-color: #9b59b6;
                color: white;
                font-weight: 600;
                padding: 11px;
                border-radius: 8px;
                border: none;
            }}
            #trialBtn:hover {{
                background-color: #8e44ad;
            }}
            #saveBtn {{
                background-color: #2ecc71;
                color: white;
                font-weight: 600;
                padding: 10px 16px;
                border-radius: 8px;
                border: none;
            }}
            #saveBtn:hover {{
                background-color: #27ae60;
            }}
            #pdfBtn {{
                background-color: #f39c12;
                color: white;
                font-weight: 600;
                padding: 10px 16px;
                border-radius: 8px;
                border: none;
            }}
            #pdfBtn:hover {{
                background-color: #d68910;
            }}
            #excelBtn {{
                background-color: #16a34a;
                color: white;
                font-weight: 600;
                padding: 10px 16px;
                border-radius: 8px;
                border: none;
            }}
            #excelBtn:hover {{
                background-color: #128a3e;
            }}
            #deleteBtn {{
                background-color: #e74c3c;
                color: white;
                font-weight: 600;
                padding: 10px 16px;
                border-radius: 8px;
                border: none;
            }}
            #deleteBtn:hover {{
                background-color: #c0392b;
            }}
            #themeBtn {{
                background-color: transparent;
                color: {text_muted};
                border: 1.5px solid {border_color};
                font-weight: 600;
                padding: 8px 10px;
                border-radius: 8px;
                font-size: 11px;
            }}
            #themeBtn:hover {{
                background-color: {border_color};
            }}
            #errorLabel {{
                color: #ff6b6b;
                font-size: 12px;
                margin-top: 8px;
            }}
            QTableWidget, QListWidget {{
                background-color: {table_bg};
                border: 1px solid {border_color};
                border-radius: 10px;
                gridline-color: {border_color};
                color: {table_text};
                selection-background-color: #2e3a52;
            }}
            QTableWidget::item, QListWidget::item {{
                padding: 6px 4px;
            }}
            QHeaderView::section {{
                background-color: #2c3547;
                color: #ffffff;
                padding: 8px;
                border: none;
                font-weight: 600;
                font-size: 12px;
            }}
            QTabWidget::pane {{
                border: none;
                margin-top: 4px;
            }}
            QTabBar::tab {{
                background-color: {tab_bg};
                color: {text_muted};
                padding: 9px 18px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-size: 12px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background-color: #4f8cff;
                color: white;
                font-weight: 600;
            }}
            QTabBar::tab:hover:!selected {{
                background-color: {border_color};
            }}
            QScrollBar:vertical {{
                background: {bg_main};
                width: 10px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical {{
                background: {border_color};
                border-radius: 5px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: #4f8cff;
            }}
        """

    def toggle_theme(self):
        self.current_theme = "light" if self.current_theme == "dark" else "dark"
        self.apply_styles()
        self.theme_btn.setText("☀️  Light Mode" if self.current_theme == "dark" else "🌙  Dark Mode")


def create_splash_pixmap():
    pixmap = QPixmap(500, 300)
    pixmap.fill(QColor("#1a1f2b"))

    painter = QPainter(pixmap)
    painter.setPen(QColor("#4f8cff"))
    title_font = QFont("Segoe UI", 22, QFont.Bold)
    painter.setFont(title_font)
    painter.drawText(pixmap.rect().adjusted(0, -30, 0, 0), Qt.AlignCenter, "Concrete Mix Design")

    painter.setPen(QColor("#8b94a8"))
    sub_font = QFont("Segoe UI", 11)
    painter.setFont(sub_font)
    painter.drawText(pixmap.rect().adjusted(0, 40, 0, 0), Qt.AlignCenter, "ACI 211.1  •  IS 10262  •  BS/DOE")

    painter.setPen(QColor("#5b6b8c"))
    small_font = QFont("Segoe UI", 9)
    painter.setFont(small_font)
    painter.drawText(pixmap.rect().adjusted(0, 100, 0, -20), Qt.AlignBottom | Qt.AlignHCenter, "Loading...")

    painter.end()
    return pixmap


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    splash_pix = create_splash_pixmap()
    splash = QSplashScreen(splash_pix)
    splash.show()
    app.processEvents()

    window = MixDesignApp()

    def show_main_window():
        window.show()
        splash.finish(window)

    QTimer.singleShot(1500, show_main_window)

    sys.exit(app.exec())
