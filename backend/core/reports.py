"""
core/reports.py
Generates CSV, JSON, and PDF reports from a scan result.
"""

import csv
import io
import json

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer


def to_json(scan: dict) -> bytes:
    return json.dumps(scan, indent=2).encode("utf-8")


def to_csv(scan: dict) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Port", "Protocol", "State", "Service", "Version", "Risk", "Description"])
    for r in scan.get("results", []):
        writer.writerow([r["port"], r["protocol"], r["state"], r["service"],
                          r["version"], r["risk"], r["description"]])
    return buf.getvalue().encode("utf-8")


def to_pdf(scan: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, title="CyberRecon Pro Report")
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("CyberRecon Pro — Scan Report", styles["Title"]))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"Target: {scan.get('target')}", styles["Normal"]))
    elements.append(Paragraph(f"Resolved IP: {scan.get('resolved_ip')}", styles["Normal"]))
    elements.append(Paragraph(f"Scan Type: {scan.get('scan_type')}", styles["Normal"]))
    elements.append(Paragraph(f"Duration: {scan.get('duration_sec')}s", styles["Normal"]))
    elements.append(Paragraph(f"Risk Score: {scan.get('risk_score')}/100", styles["Normal"]))
    elements.append(Spacer(1, 16))

    open_ports = [r for r in scan.get("results", []) if r["state"] == "open"]
    data = [["Port", "Service", "Version", "Risk", "Description"]]
    for r in open_ports:
        data.append([str(r["port"]), r["service"], r["version"][:30], r["risk"], r["description"][:60]])

    if len(data) == 1:
        data.append(["-", "No open ports found", "-", "-", "-"])

    table = Table(data, colWidths=[40, 70, 100, 50, 200])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
    ]))
    elements.append(table)

    doc.build(elements)
    return buf.getvalue()