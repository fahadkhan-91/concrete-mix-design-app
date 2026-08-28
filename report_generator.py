from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from datetime import datetime


def generate_pdf_report(file_path, project_name, inputs, mix_result, batch_info,
                         cost_info, chart_image_paths=None, trial_result=None):
    doc = SimpleDocTemplate(file_path, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "TitleStyle", parent=styles["Heading1"], fontSize=18, spaceAfter=6,
        textColor=colors.HexColor("#1e2530")
    )
    subtitle_style = ParagraphStyle(
        "SubtitleStyle", parent=styles["Normal"], fontSize=10, textColor=colors.grey, spaceAfter=16
    )
    section_style = ParagraphStyle(
        "SectionStyle", parent=styles["Heading2"], fontSize=13, spaceBefore=14, spaceAfter=8,
        textColor=colors.HexColor("#2c3e50")
    )
    subsection_style = ParagraphStyle(
        "SubsectionStyle", parent=styles["Heading3"], fontSize=11, spaceBefore=10, spaceAfter=6,
        textColor=colors.HexColor("#4f5b6d")
    )

    elements = []

    # ---------- Header ----------
    elements.append(Paragraph("Concrete Mix Design Report", title_style))
    elements.append(Paragraph(f"Project: {project_name or 'Untitled'}", subtitle_style))
    elements.append(Paragraph(
        f"Method: ACI 211.1 &nbsp;&nbsp;|&nbsp;&nbsp; Generated: {datetime.now().strftime('%d %b %Y, %I:%M %p')}",
        subtitle_style
    ))

    # ---------- Section 1: Structured Input Summary ----------
    elements.append(Paragraph("1. Input Summary", section_style))

    elements.append(Paragraph("Design Parameters", subsection_style))
    design_rows = [
        ["Parameter", "Value"],
        ["Target Strength (f'ck)", f"{inputs['fck']} MPa"],
        ["Slump", f"{inputs['slump']} mm"],
        ["Max Aggregate Size", f"{inputs['max_agg_size']} mm"],
        ["Exposure Condition", inputs['exposure'].capitalize()],
        ["Fineness Modulus of Sand", inputs['fm_sand']],
    ]
    elements.append(make_table(design_rows))

    elements.append(Paragraph("Aggregate Moisture Correction", subsection_style))
    moisture_rows = [
        ["Parameter", "Value"],
        ["Fine Aggregate Moisture", f"{inputs.get('fine_moisture', 0)}%"],
        ["Fine Aggregate Absorption", f"{inputs.get('fine_absorption', 0)}%"],
        ["Coarse Aggregate Moisture", f"{inputs.get('coarse_moisture', 0)}%"],
        ["Coarse Aggregate Absorption", f"{inputs.get('coarse_absorption', 0)}%"],
    ]
    elements.append(make_table(moisture_rows))

    elements.append(Paragraph("Batch / Site Quantity Settings", subsection_style))
    settings_rows = [
        ["Parameter", "Value"],
        ["Total Volume Required", f"{inputs.get('volume', 1)} m³"],
        ["Cement Bag Weight", f"{inputs.get('bag_weight', 50)} kg"],
    ]
    elements.append(make_table(settings_rows))

    rates_rows = [
        ["Parameter", "Value"],
        ["Cement Rate", f"{inputs.get('cement_rate', 0)} per bag"],
        ["Fine Aggregate Rate", f"{inputs.get('fine_rate', 0)} per kg"],
        ["Coarse Aggregate Rate", f"{inputs.get('coarse_rate', 0)} per kg"],
        ["Water Rate", f"{inputs.get('water_rate', 0)} per liter"],
    ]
    if any(float(inputs.get(k, 0) or 0) > 0 for k in ("cement_rate", "fine_rate", "coarse_rate", "water_rate")):
        elements.append(Paragraph("Material Rates", subsection_style))
        elements.append(make_table(rates_rows))

    elements.append(PageBreak())

    # ---------- Section 2: Complete Results ----------
    elements.append(Paragraph("2. Mix Design Results", section_style))

    elements.append(Paragraph("Design Ratios", subsection_style))
    ratio_rows = [
        ["Parameter", "Value"],
        ["Slump Category", mix_result["slump_category"]],
        ["W/C Ratio (strength-based)", mix_result["wc_strength"]],
        ["W/C Ratio (exposure limit)", mix_result["wc_limit"]],
        ["Final W/C Ratio Used", mix_result["wc_final"]],
        ["Coarse Aggregate Fraction", mix_result["coarse_fraction"]],
        ["Air Content", f'{mix_result["air_percent"]}%'],
    ]
    elements.append(make_table(ratio_rows))

    elements.append(Paragraph("Batch (Dry / Lab) Quantities — per m³", subsection_style))
    batch_dry_rows = [
        ["Parameter", "Value"],
        ["Water", f'{mix_result["water_batch"]} kg'],
        ["Cement", f'{mix_result["cement_batch"]} kg'],
        ["Fine Aggregate", f'{mix_result["fine_batch"]} kg'],
        ["Coarse Aggregate", f'{mix_result["coarse_batch"]} kg'],
    ]
    elements.append(make_table(batch_dry_rows))

    elements.append(Paragraph("Field (Moisture Adjusted) Quantities — per m³", subsection_style))
    field_rows = [
        ["Parameter", "Value"],
        ["Water", f'{mix_result["water_field"]} kg'],
        ["Cement", f'{mix_result["cement_field"]} kg'],
        ["Fine Aggregate", f'{mix_result["fine_field"]} kg'],
        ["Coarse Aggregate", f'{mix_result["coarse_field"]} kg'],
    ]
    elements.append(make_table(field_rows))

    elements.append(Paragraph("Site Batching", subsection_style))
    site_rows = [
        ["Parameter", "Value"],
        ["Total Volume", f'{batch_info["volume_m3"]} m³'],
        ["Cement Bags per m³", batch_info["bags_per_m3"]],
        ["Water per Bag", f'{batch_info["water_per_bag"]} kg'],
        ["Fine Aggregate per Bag", f'{batch_info["fine_per_bag"]} kg'],
        ["Coarse Aggregate per Bag", f'{batch_info["coarse_per_bag"]} kg'],
        ["Total Cement Bags", batch_info["total_bags"]],
        ["Total Cement", f'{batch_info["total_cement_kg"]} kg'],
        ["Total Water", f'{batch_info["total_water_kg"]} kg'],
        ["Total Fine Aggregate", f'{batch_info["total_fine_kg"]} kg'],
        ["Total Coarse Aggregate", f'{batch_info["total_coarse_kg"]} kg'],
    ]
    elements.append(make_table(site_rows))

    if cost_info and cost_info.get("total_cost", 0) > 0:
        elements.append(Paragraph("Cost Estimation", subsection_style))
        cost_rows = [
            ["Item", "Cost"],
            ["Cement", cost_info["cement_cost"]],
            ["Fine Aggregate", cost_info["fine_cost"]],
            ["Coarse Aggregate", cost_info["coarse_cost"]],
            ["Water", cost_info["water_cost"]],
            ["Total Cost", cost_info["total_cost"]],
            ["Cost per m³", cost_info["cost_per_m3"]],
        ]
        elements.append(make_table(cost_rows))

    # ---------- Section 3: Trial Mix Adjustment (agar computed ho) ----------
    if trial_result:
        elements.append(PageBreak())
        elements.append(Paragraph("3. Trial Mix Adjustment", section_style))
        trial_rows = [
            ["Parameter", "Value"],
            ["Target Slump", f'{trial_result["target_slump"]} mm'],
            ["Actual Measured Slump", f'{trial_result["actual_slump"]} mm'],
            ["Slump Difference", f'{trial_result["slump_difference"]} mm'],
            ["Water Correction", f'{trial_result["water_correction"]} kg/m³'],
            ["Adjusted Water", f'{trial_result["adjusted_water"]} kg/m³'],
            ["Adjusted Cement", f'{trial_result["adjusted_cement"]} kg/m³'],
        ]
        elements.append(make_table(trial_rows))

    # ---------- Section 4: Charts ----------
    if chart_image_paths:
        elements.append(PageBreak())
        section_num = "4" if trial_result else "3"
        elements.append(Paragraph(f"{section_num}. Visual Summary", section_style))

        pie_path = chart_image_paths.get("pie")
        bar_path = chart_image_paths.get("bar")
        compare_path = chart_image_paths.get("compare")
        wc_path = chart_image_paths.get("wc")

        if pie_path:
            elements.append(Image(pie_path, width=8*cm, height=6.5*cm))
            elements.append(Spacer(1, 10))
        if bar_path:
            elements.append(Image(bar_path, width=8*cm, height=6.5*cm))
        if compare_path:
            elements.append(PageBreak())
            elements.append(Image(compare_path, width=8*cm, height=6.5*cm))
            elements.append(Spacer(1, 10))
        if wc_path:
            elements.append(Image(wc_path, width=8*cm, height=6.5*cm))

    elements.append(Spacer(1, 20))
    elements.append(Paragraph(
        "This report is generated based on ACI 211.1 standard mix design procedure. "
        "Actual site trial mixes are recommended before full-scale production.",
        subtitle_style
    ))

    doc.build(elements)


def make_table(rows):
    table = Table(rows, colWidths=[9*cm, 7*cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3547")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f6f8")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("SPACEAFTER", (0, 0), (-1, -1), 10),
    ]))
    return table
