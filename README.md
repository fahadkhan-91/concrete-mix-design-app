# Concrete Mix Design — ACI 211.1

A desktop application for civil engineers to design concrete mixes using the ACI 211.1 standard method. Built with PySide6 (Qt), it calculates cement, water, and aggregate quantities, adjusts for site moisture, estimates cost, and generates professional PDF reports.

![Main Window](screenshots/main-window.png)

## Features

- **ACI 211.1 Mix Design Engine** — water content, w/c ratio, and coarse aggregate volume calculated from standard ACI tables with interpolation
- **Exposure-Based Durability Limits** — automatically applies stricter w/c ratio and air content for moderate/severe exposure conditions
- **Aggregate Moisture Correction** — converts lab (dry) batch quantities into real site (field) quantities based on measured moisture and absorption
- **Site Batching** — calculates cement bags per m³ and total material quantities for any project volume
- **Cost Estimation** — computes total project cost from user-supplied material rates
- **Trial Mix Adjustment** — corrects water and cement content based on actual measured slump from a site trial batch
- **Charts & Visualization** — pie chart for mix composition, bar chart for cost breakdown
- **Save/Load Projects** — SQLite-based storage with search, so past designs can be reloaded anytime
- **PDF Report Export** — generates a complete, formatted PDF report including charts, ready to share or print

## Screenshots

| Charts | Saved Projects |
|---|---|
| ![Charts](screenshots/charts.png) | ![Saved Projects](screenshots/saved-projects.png) |

## Download

Pre-built Windows installer is available on the [Releases](../../releases) page — no Python installation required. Download `ConcreteMixDesignSetup.exe`, run it, and follow the setup wizard.

## Running from Source

**Requirements:** Python 3.10+

```bash
pip install -r requirements.txt
python app.py
```

## Building the Executable

```bash
python -m PyInstaller --name="ConcreteMixDesign" --windowed --onefile --hidden-import=logic.mix_design --collect-all=numpy app.py
```

The executable will be created in the `dist/` folder.

## Tech Stack

- **PySide6** — desktop GUI
- **SQLite** — local project storage
- **Matplotlib** — charts
- **ReportLab** — PDF report generation
- **PyInstaller** — standalone executable packaging

## Method Reference

Mix design calculations follow the **ACI 211.1: Standard Practice for Selecting Proportions for Normal, Heavyweight, and Mass Concrete**.

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
