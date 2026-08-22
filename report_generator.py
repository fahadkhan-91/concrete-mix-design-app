from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from datetime import datetime


def generate_pdf_report(file_path, project_name, inputs, mix_result, batch_info, cost_info):
    doc = SimpleDocTemplate(file_path, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "TitleStyle", parent=styles["Heading1"], fontSize=18, spaceAfter=6, textColor=colors.HexColor("#1e2530")
    )
    subtitle_style = ParagraphStyle(
        "SubtitleStyle", parent=styles["Normal"], fontSize=10, textColor=colors.grey, spaceAfter=16
    )
    section_style = ParagraphStyle(
        "SectionStyle", parent=styles["Heading2"], fontSize=13, spaceBefore=14, spaceAfter=8,
        textColor=colors.HexColor("#2c3e50")
    )

    elements = []

    # header
    elements.append(Paragraph(f"Concrete Mix Design Report", title_style))
    elements.append(Paragraph(f"Project: {project_name or 'Untitled'}", subtitle_style))
    elements.append(Paragraph(
        f"Method: ACI 211.1 &nbsp;&nbsp;|&nbsp;&nbsp; Generated: {datetime.now().strftime('%d %b %Y, %I:%M %p')}",
        subtitle_style
    ))

    # section 1: input parameters
    elements.append(Paragraph("1. Design Parameters", section_style))
    input_rows = [
        ["Parameter", "Value"],
        ["Target Strength (f'ck)", f"{inputs['fck']} MPa"],
        ["Slump", f"{inputs['slump']} mm"],
        ["Max Aggregate Size", f"{inputs['max_agg_size']} mm"],
        ["Exposure Condition", inputs['exposure'].capitalize()],
        ["Fineness Modulus of Sand", inputs['fm_sand']],
    ]
    elements.append(make_table(input_rows))

    # section 2: mix design results
    elements.append(Paragraph("2. Mix Design Results (per m³)", section_style))
    mix_rows = [
        ["Parameter", "Value"],
        ["Slump Category", mix_result["slump_category"]],
        ["Final W/C Ratio Used", mix_result["wc_final"]],
        ["Air Content", f'{mix_result["air_percent"]}%'],
        ["Water (field, adjusted)", f'{mix_result["water_field"]} kg'],
        ["Cement (field)", f'{mix_result["cement_field"]} kg'],
        ["Fine Aggregate (field)", f'{mix_result["fine_field"]} kg'],
        ["Coarse Aggregate (field)", f'{mix_result["coarse_field"]} kg'],
    ]
    elements.append(make_table(mix_rows))

    # section 3: site batching
    elements.append(Paragraph("3. Site Batching Quantities", section_style))
    site_rows = [
        ["Parameter", "Value"],
        ["Total Volume", f'{batch_info["volume_m3"]} m³'],
        ["Cement Bags per m³", batch_info["bags_per_m3"]],
        ["Total Cement Bags", batch_info["total_bags"]],
        ["Total Cement", f'{batch_info["total_cement_kg"]} kg'],
        ["Total Water", f'{batch_info["total_water_kg"]} kg'],
        ["Total Fine Aggregate", f'{batch_info["total_fine_kg"]} kg'],
        ["Total Coarse Aggregate", f'{batch_info["total_coarse_kg"]} kg'],
    ]
    elements.append(make_table(site_rows))

    # section 4: cost estimation (agar rates diye gaye hon)
    if cost_info and cost_info.get("total_cost", 0) > 0:
        elements.append(Paragraph("4. Cost Estimation", section_style))
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
    ]))
    return table
