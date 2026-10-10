#!/usr/bin/env python3
"""Create the verified Word report from the latest simulation artifacts."""
from pathlib import Path
import json
import joblib
import pandas as pd
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from heater_controller.training import load_training_csv, chronological_split, regression_metrics

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "heater_controller_simulation_report.docx"

def shade(cell, color):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd"); shd.set(qn("w:fill"), color); tc_pr.append(shd)

def borders(table):
    tbl_pr = table._tbl.tblPr
    node = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        item = OxmlElement(f"w:{edge}")
        item.set(qn("w:val"), "single"); item.set(qn("w:sz"), "6")
        item.set(qn("w:color"), "D9D9D9"); node.append(item)
    tbl_pr.append(node)

def set_cell_text(cell, text, bold=False, color="000000", align=WD_ALIGN_PARAGRAPH.LEFT):
    cell.text = ""
    p = cell.paragraphs[0]; p.alignment = align
    r = p.add_run(str(text)); r.bold = bold; r.font.name = "Aptos"; r.font.size = Pt(9); r.font.color.rgb = RGBColor.from_string(color)
    cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    tc = cell._tc.get_or_add_tcPr(); mar = OxmlElement("w:tcMar")
    for side in ("top", "left", "bottom", "right"):
        n = OxmlElement(f"w:{side}"); n.set(qn("w:w"), "100"); n.set(qn("w:type"), "dxa"); mar.append(n)
    tc.append(mar)

def add_table(doc, headers, rows, widths=None):
    table = doc.add_table(rows=1, cols=len(headers)); table.autofit = False; borders(table)
    table.rows[0]._tr.get_or_add_trPr().append(OxmlElement("w:tblHeader"))
    for i, h in enumerate(headers):
        shade(table.rows[0].cells[i], "1F4E78")
        set_cell_text(table.rows[0].cells[i], h, True, "FFFFFF", WD_ALIGN_PARAGRAPH.CENTER)
        if widths: table.rows[0].cells[i].width = Inches(widths[i])
    for ri, row in enumerate(rows):
        cells = table.add_row().cells
        for i, value in enumerate(row):
            if ri % 2: shade(cells[i], "EAF2F8")
            set_cell_text(cells[i], value, align=WD_ALIGN_PARAGRAPH.LEFT if i == 0 else WD_ALIGN_PARAGRAPH.CENTER)
            if widths: cells[i].width = Inches(widths[i])
    doc.add_paragraph().paragraph_format.space_after = Pt(0)
    return table

def keep_with_next(paragraph):
    paragraph.paragraph_format.keep_with_next = True

def main():
    summary = pd.read_csv(ROOT / "artifacts/evaluation/simulated_summary.csv")
    training = load_training_csv(ROOT / "artifacts/simulated_training.csv")
    ordered = training.copy(); ordered["target_temp"] = ordered.indoor_temp.shift(-1)
    _, validation, test = chronological_split(ordered.dropna())
    model = joblib.load(ROOT / "artifacts/heater_mlp.joblib")["model"]
    metrics = {
        "Validation MLP": regression_metrics(validation.target_temp, model.predict(validation[["indoor_temp", "outdoor_temp", "heater_duty"]])),
        "Test MLP": regression_metrics(test.target_temp, model.predict(test[["indoor_temp", "outdoor_temp", "heater_duty"]])),
        "Test persistence": regression_metrics(test.target_temp, test.indoor_temp),
    }

    doc = Document()
    sec = doc.sections[0]; sec.page_width = Inches(8.5); sec.page_height = Inches(11)
    sec.top_margin = Inches(.72); sec.bottom_margin = Inches(.72); sec.left_margin = Inches(.78); sec.right_margin = Inches(.78)
    styles = doc.styles
    normal = styles["Normal"]; normal.font.name = "Aptos"; normal.font.size = Pt(10.5); normal.font.color.rgb = RGBColor(0,0,0)
    normal.paragraph_format.space_after = Pt(6); normal.paragraph_format.line_spacing = 1.08
    for name, size in (("Title", 25), ("Heading 1", 16), ("Heading 2", 12)):
        s = styles[name]; s.font.name = "Aptos Display"; s.font.size = Pt(size); s.font.color.rgb = RGBColor(0,0,0); s.font.bold = True
        s.paragraph_format.space_before = Pt(12); s.paragraph_format.space_after = Pt(6); s.paragraph_format.keep_with_next = True
        s.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    styles["Title"].paragraph_format.space_before = Pt(0); styles["Title"].paragraph_format.space_after = Pt(7)
    title_ppr = styles["Title"]._element.get_or_add_pPr()
    title_border = title_ppr.find(qn("w:pBdr"))
    if title_border is not None: title_ppr.remove(title_border)

    title = doc.add_paragraph(style="Title"); title.add_run("Simulated Price Aware Heater Controller Results")
    subtitle = doc.add_paragraph(); subtitle.alignment = WD_ALIGN_PARAGRAPH.LEFT
    run = subtitle.add_run("CPU prototype training and controller evaluation"); run.bold = True; run.font.size = Pt(12)
    meta = doc.add_paragraph("Report date 10 October 2026  |  Raspberry Pi 3B target  |  Simulation only")
    meta.runs[0].font.size = Pt(9); meta.runs[0].font.color.rgb = RGBColor(80,80,80)

    doc.add_heading("Conclusion", level=1)
    doc.add_paragraph("The CPU trained MLP predicted simulated next hour indoor temperature substantially better than the persistence baseline. In the common controller simulation, the MLP based controller used the least estimated energy and produced the lowest comfort violation, while the simpler price aware rule produced the lowest spot price cost. These are simulator results, not measurements from a Swedish home.")

    doc.add_heading("Model performance", level=1)
    doc.add_paragraph("The predictor uses current indoor temperature, outdoor temperature, and simulated heater duty. Electricity price is excluded from the thermal predictor and enters only the controller cost calculation.")
    metric_rows = [(name, f"{v['mae_c']:.3f}", f"{v['rmse_c']:.3f}") for name, v in metrics.items()]
    add_table(doc, ["Evaluation", "MAE °C", "RMSE °C"], metric_rows, [3.5, 1.35, 1.35])
    doc.add_paragraph("The test MLP reduced MAE by 81.1 percent relative to persistence on the simulated test partition. The unusually small error reflects a simple, deterministic one zone simulator and should not be treated as expected real building accuracy.")

    doc.add_heading("Controller comparison", level=1)
    doc.add_paragraph("Each controller used the same 7,079 hour outdoor temperature and SE3 price profile, 2.0 kW heater rating, initial indoor temperature, and thermal simulator.")
    rows = []
    labels = {"static_hysteresis":"Static hysteresis", "price_aware_rule":"Price aware rule", "mlp_price_aware":"MLP price aware"}
    for _, r in summary.iterrows():
        rows.append((labels[r.controller], f"{r.estimated_cost:.2f}", f"{r.estimated_energy_kwh:,.1f}",
                     f"{int(r.hours_outside_comfort):,}", f"{r.degree_hours_outside:,.1f}", f"{int(r.heater_switches):,}"))
    add_table(doc, ["Controller", "Cost EUR", "Energy kWh", "Hours outside", "Degree hours", "Switches"], rows,
              [1.65, .85, 1.05, 1.0, 1.0, .75])
    doc.add_paragraph("Cost uses SE3 spot price converted from EUR per MWh to EUR per kWh. It excludes taxes, network charges, retailer fees, and currency conversion. Energy equals heater power in kW multiplied by duty and one hour.")

    doc.add_heading("Interpretation", level=1)
    p = doc.add_paragraph(); p.add_run("Static hysteresis. ").bold = True; p.add_run("This controller is simple but reacts only after temperature crosses a threshold. It consumed the most energy and had the highest simulated cost.")
    p = doc.add_paragraph(); p.add_run("Price aware rule. ").bold = True; p.add_run("This controller shifted some heating toward cheaper hours and achieved the lowest spot price cost, but frequent fractional duty changes increased its switch count and comfort performance remained weak.")
    p = doc.add_paragraph(); p.add_run("MLP price aware controller. ").bold = True; p.add_run("This controller achieved the lowest energy use, fewest switches, and lowest degree hour violation. Its cost was slightly higher than the rule controller because its optimization placed greater weight on comfort.")

    doc.add_heading("Training method", level=1)
    doc.add_paragraph("The thermal simulator generated heater duty and corresponding indoor temperature response because the prototype has no physical sensors. The model pipeline uses StandardScaler followed by MLPRegressor with hidden layers of 8 and 4 neurons and ReLU activation. Rows were split chronologically into 70 percent training, 15 percent validation, and 15 percent testing, with no random row shuffle.")
    add_table(doc, ["Item", "Value"], [
        ("Prepared hourly profile", "7,079 UTC hours"),
        ("Training source", "Thermal simulator with simulated heater duty"),
        ("Features", "Indoor temperature, outdoor temperature, heater duty"),
        ("Target", "Indoor temperature one hour ahead"),
        ("Model", "StandardScaler and MLPRegressor 8 by 4 ReLU"),
        ("Split", "Chronological 70 percent 15 percent 15 percent"),
        ("Test status", "5 focused tests passed"),
    ], [2.05, 4.25])

    doc.add_heading("Data provenance", level=1)
    doc.add_paragraph("Outdoor temperature came from the repository SMHI export and prices came from SE3 records in the repository electricity price export. The SML2010 files remain a separate source for indoor temperature patterns only. Their motor state fields are not verified electric heater duty and were not treated as heater state. This report does not represent SML2010 combined with Swedish weather as measurements from one Swedish home.")

    doc.add_heading("Limitations and safety", level=1)
    doc.add_paragraph("The simulator assumes one well mixed thermal zone with fixed heat loss and heater gain. It omits occupancy, solar gain, wind, humidity, detailed thermal mass, equipment cycling constraints, sensor error, and distribution charges. The model requires simulated or measured heater duty examples to learn heating response. Parameters must be calibrated and validation must use real sensor data before considering deployment.")
    safety = doc.add_paragraph(); safety.add_run("Safety. ").bold = True
    safety.add_run("This prototype must not connect Raspberry Pi GPIO directly to a mains powered heater. All operation in this report is simulated.")

    doc.add_heading("Reproduction commands", level=1)
    commands = [
        "python -m scripts.prepare_data --smhi datas/temperatureData.csv --prices datas/pricedataSweden.csv --output artifacts/hourly_profile.csv",
        "python -m scripts.generate_training_data artifacts/hourly_profile.csv --output artifacts/simulated_training.csv",
        "python -m scripts.train_mlp artifacts/simulated_training.csv --model artifacts/heater_mlp.joblib --predictions artifacts/test_predictions.csv",
        "python -m scripts.compare_controllers artifacts/hourly_profile.csv artifacts/heater_mlp.joblib --heater-power-kw 2.0 --output-dir artifacts/evaluation",
        "python -m pytest -q",
    ]
    for command in commands:
        p = doc.add_paragraph(style=None); p.paragraph_format.left_indent = Inches(.2); p.paragraph_format.space_after = Pt(4)
        r = p.add_run(command); r.font.name = "Aptos Mono"; r.font.size = Pt(8.5)

    doc.add_heading("Generated artifacts", level=1)
    for artifact in ("artifacts/heater_mlp.joblib", "artifacts/test_predictions.csv",
                     "artifacts/evaluation/simulated_summary.csv", "artifacts/evaluation/*_simulated.csv"):
        p = doc.add_paragraph(style=None); p.style = doc.styles["List Bullet"]
        r = p.add_run(artifact); r.font.name = "Aptos Mono"; r.font.size = Pt(9)

    for section in doc.sections:
        footer = section.footer.paragraphs[0]; footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = footer.add_run("Simulated heater controller results  |  Simulation only  |  "); r.font.size = Pt(8); r.font.color.rgb = RGBColor(90,90,90)
        fld = OxmlElement("w:fldSimple"); fld.set(qn("w:instr"), "PAGE"); footer._p.append(fld)
    OUT.parent.mkdir(parents=True, exist_ok=True); doc.save(OUT)
    print(OUT)

if __name__ == "__main__": main()
