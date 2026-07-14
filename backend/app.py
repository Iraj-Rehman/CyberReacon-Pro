"""
app.py — CyberRecon Pro backend

Run: python app.py
Then open the frontend (see frontend/README instructions).
"""

import json
import os
import threading
import time
import uuid
from datetime import datetime

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import io

from core.scanner import (
    QUICK_PORTS, FULL_PORTS, parse_port_spec,
    resolve_target, scan_single_port, PORT_INTEL,
)
from core.discovery import discover_network
from core.system_stats import get_system_stats
from core import reports

app = Flask(__name__)
CORS(app)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
HISTORY_FILE = os.path.join(DATA_DIR, "history.json")
os.makedirs(DATA_DIR, exist_ok=True)
if not os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, "w") as f:
        json.dump([], f)

# In-memory job store: job_id -> { status, progress, logs, results, ... }
JOBS = {}
JOBS_LOCK = threading.Lock()

RISK_WEIGHT = {"critical": 25, "high": 15, "medium": 8, "low": 3, "none": 0}


def _load_history():
    with open(HISTORY_FILE) as f:
        return json.load(f)


def _save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


def _calc_risk_score(results):
    score = sum(RISK_WEIGHT.get(r["risk"], 0) for r in results if r["state"] == "open")
    return min(100, score)


def _run_scan_job(job_id: str, target: str, scan_type: str, custom_ports: str, grab_banners: bool):
    job = JOBS[job_id]
    start = time.time()

    try:
        ip = resolve_target(target)
    except Exception:
        job["status"] = "error"
        job["logs"].append("[ERROR] Could not resolve target.")
        return

    job["logs"].append(f"[INFO] Resolved {target} -> {ip}")
    job["resolved_ip"] = ip

    if scan_type == "quick":
        ports = QUICK_PORTS
    elif scan_type == "full":
        ports = FULL_PORTS
    else:
        try:
            ports = parse_port_spec(custom_ports or "1-1024")
        except Exception:
            job["status"] = "error"
            job["logs"].append("[ERROR] Invalid custom port spec.")
            return

    job["logs"].append(f"[INFO] Starting {scan_type} scan — {len(ports)} ports queued")
    total = len(ports)
    results = []

    for i, port in enumerate(ports, start=1):
        if job["status"] == "stopped":
            job["logs"].append("[WARN] Scan stopped by user.")
            break

        r = scan_single_port(ip, port, grab_banners=grab_banners)
        results.append(r)

        if r["state"] == "open":
            job["logs"].append(f"[OPEN] Port {port} ({r['service']}) is open — risk: {r['risk']}")
        job["progress"] = round((i / total) * 100, 1)
        job["results"] = results

    duration = round(time.time() - start, 2)
    job["logs"].append(f"[INFO] Scan complete in {duration}s")
    job["status"] = "completed" if job["status"] != "stopped" else "stopped"
    job["duration_sec"] = duration

    open_count = sum(1 for r in results if r["state"] == "open")
    closed_count = sum(1 for r in results if r["state"] == "closed")
    risk_score = _calc_risk_score(results)

    scan_record = {
        "id": job_id,
        "target": target,
        "resolved_ip": ip,
        "scan_type": scan_type,
        "date": datetime.now().isoformat(timespec="seconds"),
        "duration_sec": duration,
        "total_ports": total,
        "open_ports": open_count,
        "closed_ports": closed_count,
        "risk_score": risk_score,
        "results": results,
    }
    job["record"] = scan_record

    history = _load_history()
    history.insert(0, scan_record)
    _save_history(history[:100])  # keep last 100 scans


@app.route("/api/scan/start", methods=["POST"])
def start_scan():
    data = request.get_json()
    target = (data.get("target") or "").strip()
    scan_type = data.get("scan_type", "quick")
    custom_ports = data.get("ports", "")
    grab_banners = data.get("grab_banners", True)

    if not target:
        return jsonify({"error": "Target is required"}), 400

    job_id = str(uuid.uuid4())
    with JOBS_LOCK:
        JOBS[job_id] = {
            "status": "running",
            "progress": 0,
            "logs": [f"[INFO] Job {job_id[:8]} created for target {target}"],
            "results": [],
            "resolved_ip": None,
            "duration_sec": None,
            "record": None,
        }

    thread = threading.Thread(
        target=_run_scan_job,
        args=(job_id, target, scan_type, custom_ports, grab_banners),
        daemon=True,
    )
    thread.start()

    return jsonify({"job_id": job_id})


@app.route("/api/scan/status/<job_id>", methods=["GET"])
def scan_status(job_id):
    job = JOBS.get(job_id)
    if not job:
        return jsonify({"error": "Unknown job id"}), 404
    return jsonify(job)


@app.route("/api/scan/stop/<job_id>", methods=["POST"])
def stop_scan(job_id):
    job = JOBS.get(job_id)
    if not job:
        return jsonify({"error": "Unknown job id"}), 404
    job["status"] = "stopped"
    return jsonify({"ok": True})


@app.route("/api/discover", methods=["POST"])
def discover():
    data = request.get_json()
    cidr = (data.get("cidr") or "").strip()
    if not cidr:
        return jsonify({"error": "CIDR is required, e.g. 192.168.1.0/24"}), 400
    try:
        devices = discover_network(cidr)
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"cidr": cidr, "count": len(devices), "devices": devices})


@app.route("/api/system-stats", methods=["GET"])
def system_stats():
    return jsonify(get_system_stats())


@app.route("/api/history", methods=["GET"])
def history():
    return jsonify(_load_history())


@app.route("/api/history/<scan_id>", methods=["DELETE"])
def delete_history_item(scan_id):
    history_data = _load_history()
    history_data = [h for h in history_data if h["id"] != scan_id]
    _save_history(history_data)
    return jsonify({"ok": True})


@app.route("/api/export/<fmt>/<scan_id>", methods=["GET"])
def export_report(fmt, scan_id):
    history_data = _load_history()
    scan = next((h for h in history_data if h["id"] == scan_id), None)
    if not scan:
        return jsonify({"error": "Scan not found"}), 404

    if fmt == "json":
        content = reports.to_json(scan)
        mimetype = "application/json"
        filename = f"scan_{scan_id[:8]}.json"
    elif fmt == "csv":
        content = reports.to_csv(scan)
        mimetype = "text/csv"
        filename = f"scan_{scan_id[:8]}.csv"
    elif fmt == "pdf":
        content = reports.to_pdf(scan)
        mimetype = "application/pdf"
        filename = f"scan_{scan_id[:8]}.pdf"
    else:
        return jsonify({"error": "Unsupported format"}), 400

    return send_file(io.BytesIO(content), mimetype=mimetype, as_attachment=True, download_name=filename)


@app.route("/api/port-intel", methods=["GET"])
def port_intel():
    """Static reference table the frontend can use for a 'Security Intelligence' view."""
    return jsonify(PORT_INTEL)


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "time": datetime.now().isoformat()})


if __name__ == "__main__":
    app.run(debug=False, port=5000, threaded=True)