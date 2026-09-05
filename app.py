from flask import Flask, jsonify, request, send_from_directory, send_file
from flask_cors import CORS
from datetime import datetime, timedelta
from io import BytesIO, StringIO
import csv
import json
import os
import re

app = Flask(__name__)
CORS(app)

# =========================================================
# SHARED + PERSISTENT MPLADS PROJECT DATA
# =========================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_STORE_FILE = os.path.join(BASE_DIR, "projects_data.json")

# All project money values are stored internally in RUPEES LAKH.
# Example: sanctioned=10 means ₹10 lakh.
MAX_REASONABLE_PROJECT_LAKH = 5000.0  # ₹50 crore safety ceiling for this prototype
LEGACY_RUPEE_GUESS_THRESHOLD = 5000.0
VALID_AMOUNT_UNITS = {"rupees", "lakh", "crore"}

DEFAULT_PROJECTS = [
    {"id": "MPL-1001", "name": "Road Construction", "district": "Jaipur", "sanctioned": 10, "spent": 9.2, "progress": 92},
    {"id": "MPL-1002", "name": "Community Hall", "district": "Kota", "sanctioned": 15, "spent": 11, "progress": 73},
    {"id": "MPL-1003", "name": "Water Tank", "district": "Ajmer", "sanctioned": 8, "spent": 7.8, "progress": 98},
    {"id": "MPL-1004", "name": "School Building", "district": "Jodhpur", "sanctioned": 20, "spent": 25, "progress": 61},
    {"id": "MPL-1005", "name": "Street Lighting", "district": "Jaipur", "sanctioned": 6, "spent": 5.5, "progress": 90},
    {"id": "MPL-1006", "name": "Drainage System", "district": "Kota", "sanctioned": 12, "spent": 14.5, "progress": 48},
    {"id": "MPL-1007", "name": "Health Centre", "district": "Udaipur", "sanctioned": 25, "spent": 18, "progress": 72},
    {"id": "MPL-1008", "name": "Community Park", "district": "Ajmer", "sanctioned": 9, "spent": 8.5, "progress": 94},
    {"id": "MPL-1009", "name": "Road Repair", "district": "Jodhpur", "sanctioned": 11, "spent": 17, "progress": 40},
    {"id": "MPL-1010", "name": "Drinking Water Facility", "district": "Udaipur", "sanctioned": 7, "spent": 4.5, "progress": 65},
]


def _convert_to_lakh(value, unit="lakh"):
    """Convert an incoming money value to lakh, the app's canonical unit."""
    try:
        amount = float(value)
    except (TypeError, ValueError):
        raise ValueError("Amount must be numeric")

    unit = str(unit or "lakh").strip().lower()
    if unit not in VALID_AMOUNT_UNITS:
        raise ValueError("Unsupported amount unit")

    if amount < 0:
        raise ValueError("Amount cannot be negative")

    if unit == "rupees":
        amount_lakh = amount / 100000.0
    elif unit == "crore":
        amount_lakh = amount * 100.0
    else:
        amount_lakh = amount

    return round(amount_lakh, 4)


def _repair_legacy_money_value(value):
    """Repair the old UI mistake where raw rupees were accidentally stored as lakh.

    Values above ₹50 crore in 'lakh' form are implausible for this prototype.
    Old records such as 100000 / 50000 were typically rupees entered into
    a field labelled '₹ Lakh', so they are converted to 1.0 / 0.5 lakh.
    """
    amount = float(value)
    if amount > LEGACY_RUPEE_GUESS_THRESHOLD:
        return round(amount / 100000.0, 4), True
    return amount, False


def _normalize_project(raw):
    """Return (clean_project, repaired) for stored project data."""
    try:
        project_id = str(raw["id"]).strip()
        name = str(raw["name"]).strip()
        district = str(raw["district"]).strip()
        sanctioned, repaired_sanctioned = _repair_legacy_money_value(raw["sanctioned"])
        spent, repaired_spent = _repair_legacy_money_value(raw["spent"])
        progress = int(raw["progress"])
    except (KeyError, TypeError, ValueError):
        return None, False

    if not project_id or not name or not district:
        return None, False
    if sanctioned <= 0 or spent < 0 or not 0 <= progress <= 100:
        return None, False

    return {
        "id": project_id,
        "name": name,
        "district": district,
        "sanctioned": sanctioned,
        "spent": spent,
        "progress": progress,
    }, (repaired_sanctioned or repaired_spent)


def save_projects():
    """Persist the shared project dataset atomically."""
    temp_file = PROJECT_STORE_FILE + ".tmp"
    with open(temp_file, "w", encoding="utf-8") as handle:
        json.dump(projects, handle, ensure_ascii=False, indent=2)
    os.replace(temp_file, PROJECT_STORE_FILE)


def load_projects():
    """Load projects from disk; seed the file on first run."""
    if os.path.exists(PROJECT_STORE_FILE):
        try:
            with open(PROJECT_STORE_FILE, "r", encoding="utf-8") as handle:
                raw_data = json.load(handle)
            if isinstance(raw_data, list):
                cleaned = []
                repaired_any = False
                for item in raw_data:
                    project, repaired = _normalize_project(item)
                    if project:
                        cleaned.append(project)
                        repaired_any = repaired_any or repaired
                if cleaned:
                    # Persist one-time repairs so Dashboard/Analytics/Reports stay correct
                    # after the next restart as well.
                    if repaired_any:
                        # Keep a one-time backup before changing legacy values.
                        backup_file = os.path.join(BASE_DIR, "projects_data.before_money_fix.json")
                        if not os.path.exists(backup_file):
                            try:
                                with open(backup_file, "w", encoding="utf-8") as handle:
                                    json.dump(raw_data, handle, ensure_ascii=False, indent=2)
                            except OSError:
                                pass

                        temp_file = PROJECT_STORE_FILE + ".tmp"
                        with open(temp_file, "w", encoding="utf-8") as handle:
                            json.dump(cleaned, handle, ensure_ascii=False, indent=2)
                        os.replace(temp_file, PROJECT_STORE_FILE)
                        print("[MPLADS] Repaired legacy project money units; backup saved as projects_data.before_money_fix.json")
                    return cleaned
        except (OSError, json.JSONDecodeError):
            pass

    seeded = [dict(project) for project in DEFAULT_PROJECTS]
    try:
        with open(PROJECT_STORE_FILE, "w", encoding="utf-8") as handle:
            json.dump(seeded, handle, ensure_ascii=False, indent=2)
    except OSError:
        pass
    return seeded


projects = load_projects()

# =========================================================
# RISK ANALYSIS
# =========================================================

def calculate_risk(project):
    risk = 0
    reasons = []

    sanctioned = project["sanctioned"]
    spent = project["spent"]
    progress = project["progress"]

    if spent > sanctioned:
        overrun = ((spent - sanctioned) / sanctioned) * 100
        if overrun > 20:
            risk += 50
            reasons.append("Significant cost overrun detected")
        else:
            risk += 25
            reasons.append("Cost exceeds sanctioned amount")

    if progress < 50:
        risk += 35
        reasons.append("Project progress is critically low")
    elif progress < 70:
        risk += 20
        reasons.append("Project progress is below expected level")

    utilization = (spent / sanctioned) * 100 if sanctioned else 0
    if utilization < 65 and progress > 60:
        risk += 20
        reasons.append("Low fund utilization compared with project progress")

    risk = min(risk, 100)

    if risk >= 70:
        level = "High"
    elif risk >= 40:
        level = "Medium"
    else:
        level = "Low"

    return {"score": risk, "level": level, "reasons": reasons}


def analyze_projects():
    analyzed_projects = []
    for project in projects:
        analysis = calculate_risk(project)
        project_data = project.copy()
        project_data["risk_score"] = analysis["score"]
        project_data["risk_level"] = analysis["level"]
        project_data["risk_reasons"] = analysis["reasons"]
        analyzed_projects.append(project_data)
    return analyzed_projects

# =========================================================
# REPORT DATA + HELPERS
# =========================================================

REPORT_NAME_BY_TYPE = {
    "Summary": "District Summary Report",
    "Risk": "Risk Analysis Report",
    "Financial": "Fund Utilization Report",
    "Progress": "Monthly Progress Report",
    "Status": "Project Status Report",
}

REPORT_TYPES = set(REPORT_NAME_BY_TYPE)
VALID_DISTRICTS = {"Rajasthan", "Jaipur", "Kota", "Ajmer", "Jodhpur", "Udaipur"}


def seed_reports():
    """Create realistic recent history so the page starts like the reference design."""
    now = datetime.now().replace(second=0, microsecond=0)
    latest = now - timedelta(days=2)
    recent_templates = [
        ("District Summary Report", "Summary", "Jaipur", "2.4 MB"),
        ("Risk Analysis Report", "Risk", "Rajasthan", "1.8 MB"),
        ("Fund Utilization Report", "Financial", "Kota", "2.1 MB"),
        ("Monthly Progress Report", "Progress", "Ajmer", "1.6 MB"),
        ("Risk Monitoring Report", "Risk", "Rajasthan", "2.7 MB"),
        ("Project Status Report", "Status", "Jodhpur", "1.9 MB"),
        ("Executive Summary", "Summary", "Udaipur", "1.3 MB"),
        ("District Risk Review", "Risk", "Jaipur", "1.5 MB"),
    ]

    seeded = []
    # 8 reports in the same month as the latest report.
    month_start = latest.replace(day=1, hour=9, minute=0)
    for i, (name, report_type, district, size) in enumerate(recent_templates):
        day_offset = min(i // 2, max(0, latest.day - 1))
        generated = latest.replace(hour=max(9, 16 - i), minute=(i * 15) % 60) - timedelta(days=day_offset)
        if generated.month != latest.month:
            generated = month_start + timedelta(hours=i)
        seeded.append({
            "id": f"RPT-{1001 + i}",
            "name": name,
            "type": report_type,
            "district": district,
            "generated_at": generated.isoformat(),
            "size": size,
            "download_count": 7 if i < 4 else 6,
        })

    # 16 older reports from previous months.
    names = list(REPORT_NAME_BY_TYPE.items())
    districts = ["Rajasthan", "Jaipur", "Kota", "Ajmer", "Jodhpur", "Udaipur"]
    for i in range(8, 24):
        report_type, default_name = names[i % len(names)]
        generated = month_start - timedelta(days=(i - 7) * 5)
        seeded.append({
            "id": f"RPT-{1001 + i}",
            "name": default_name,
            "type": report_type,
            "district": districts[i % len(districts)],
            "generated_at": generated.replace(hour=10 + (i % 6), minute=(i * 7) % 60).isoformat(),
            "size": f"{1.2 + (i % 6) * 0.3:.1f} MB",
            "download_count": 7 if i < 12 else 6,
        })

    # Force the seeded lifetime download total to 156.
    current_total = sum(r["download_count"] for r in seeded)
    if seeded:
        seeded[0]["download_count"] += 156 - current_total
    return seeded


REPORT_STORE_FILE = os.path.join(BASE_DIR, "reports_data.json")


def save_reports():
    with open(REPORT_STORE_FILE, "w", encoding="utf-8") as handle:
        json.dump(reports, handle, ensure_ascii=False, indent=2)


def load_reports():
    if os.path.exists(REPORT_STORE_FILE):
        try:
            with open(REPORT_STORE_FILE, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            if isinstance(data, list):
                # Older report history may contain the removed standalone anomaly-report type.
                # Convert those saved records to normal Risk reports so no separate UI option returns.
                changed = False
                for report in data:
                    if str(report.get("type", "")).strip().lower() == "anomaly":
                        report["type"] = "Risk"
                        name = str(report.get("name", ""))
                        if "anomaly" in name.lower():
                            report["name"] = re.sub(
                                r"anomaly\s+detection",
                                "Risk Monitoring",
                                name,
                                flags=re.IGNORECASE,
                            )
                        changed = True
                if changed:
                    with open(REPORT_STORE_FILE, "w", encoding="utf-8") as handle:
                        json.dump(data, handle, ensure_ascii=False, indent=2)
                return data
        except (OSError, json.JSONDecodeError):
            pass
    seeded = seed_reports()
    try:
        with open(REPORT_STORE_FILE, "w", encoding="utf-8") as handle:
            json.dump(seeded, handle, ensure_ascii=False, indent=2)
    except OSError:
        pass
    return seeded


reports = load_reports()
SCHEDULED_REPORTS = 4


def get_report_projects(district):
    analyzed = analyze_projects()
    if district and district != "Rajasthan":
        analyzed = [p for p in analyzed if p["district"] == district]
    return analyzed


def build_report_summary(report):
    selected = get_report_projects(report.get("district", "Rajasthan"))
    total = len(selected)
    total_sanctioned = sum(p["sanctioned"] for p in selected)
    total_spent = sum(p["spent"] for p in selected)
    avg_progress = sum(p["progress"] for p in selected) / total if total else 0
    high_risk = sum(1 for p in selected if p["risk_level"] == "High")
    medium_risk = sum(1 for p in selected if p["risk_level"] == "Medium")
    low_risk = sum(1 for p in selected if p["risk_level"] == "Low")
    utilization = (total_spent / total_sanctioned * 100) if total_sanctioned else 0

    return {
        "total_projects": total,
        "total_sanctioned": round(total_sanctioned, 2),
        "total_spent": round(total_spent, 2),
        "avg_progress": round(avg_progress, 1),
        "high_risk": high_risk,
        "medium_risk": medium_risk,
        "low_risk": low_risk,
        "utilization": round(utilization, 1),
    }


def report_payload(report):
    data = report.copy()
    data["summary"] = build_report_summary(report)
    return data


def find_report(report_id):
    return next((r for r in reports if r["id"] == report_id), None)


def parse_iso_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def relative_time_text(iso_value):
    if not iso_value:
        return "No reports"
    dt = datetime.fromisoformat(iso_value)
    delta = datetime.now() - dt
    days = max(0, delta.days)
    if days == 0:
        return "Today"
    if days == 1:
        return "1 day ago"
    if days < 30:
        return f"{days} days ago"
    months = max(1, days // 30)
    return f"{months} month{'s' if months != 1 else ''} ago"

# =========================================================
# HOME + PUBLIC DASHBOARD DATA + EXISTING PROJECT APIS
# =========================================================

@app.route("/")
def serve_home():
    # Keep the existing website home page as the entry point.
    return send_from_directory(BASE_DIR, "home.html")


@app.route("/dashboard")
def dashboard_page():
    # One dashboard file handles both modes in the browser:
    # public searchable view before login, existing officer view after login.
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/login")
def login_page():
    return send_from_directory(BASE_DIR, "login.html")


@app.route("/api/public-projects", methods=["GET"])
def get_public_projects():
    """Read-only fields used by the public searchable dashboard.

    The current sample dataset has district but not a constituency column.
    This lightweight mapping is only display metadata for the prototype and
    does not alter projects_data.json or the officer dashboard.
    """
    constituency_by_district = {
        "Jaipur": "Jaipur",
        "Kota": "Kota-Bundi",
        "Ajmer": "Ajmer",
        "Jodhpur": "Jodhpur",
        "Udaipur": "Udaipur",
    }

    public_rows = []
    for project in projects:
        progress = int(project.get("progress", 0))
        sanctioned = float(project.get("sanctioned", 0))
        spent = float(project.get("spent", 0))

        # Keep public status counts consistent with the existing officer dashboard.
        if progress >= 90:
            status = "Completed"
        elif progress < 70:
            status = "Delayed"
        else:
            status = "Ongoing"

        district = project.get("district", "")
        public_rows.append({
            "id": project.get("id", ""),
            "name": project.get("name", ""),
            "state": "Rajasthan",
            "district": district,
            "constituency": constituency_by_district.get(district, district or "Not available"),
            "sanctioned": sanctioned,
            "spent": spent,
            "progress": progress,
            "status": status,
        })

    return jsonify(public_rows)


@app.route("/api/projects", methods=["GET"])
def get_projects():
    return jsonify(analyze_projects())


@app.route("/api/projects", methods=["POST"])
def add_project():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "No project data received"}), 400

    required_fields = ["name", "district", "sanctioned", "spent", "progress"]
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400

    amount_unit = str(data.get("amount_unit", "lakh")).strip().lower()
    try:
        sanctioned = _convert_to_lakh(data["sanctioned"], amount_unit)
        spent = _convert_to_lakh(data["spent"], amount_unit)
        progress = int(data["progress"])
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    if sanctioned <= 0 or spent < 0 or not 0 <= progress <= 100:
        return jsonify({"error": "Invalid sanctioned/spent/progress values"}), 400

    if sanctioned > MAX_REASONABLE_PROJECT_LAKH or spent > MAX_REASONABLE_PROJECT_LAKH:
        return jsonify({
            "error": (
                "Amount is unusually high. Select the correct unit (Rupees, Lakh or Crore). "
                "The system stores amounts internally in ₹ lakh."
            )
        }), 400

    existing_numbers = []
    for item in projects:
        project_id = str(item.get("id", ""))
        if project_id.startswith("MPL-"):
            try:
                existing_numbers.append(int(project_id.split("-")[-1]))
            except ValueError:
                pass

    new_project = {
        "id": f"MPL-{max(existing_numbers + [1000]) + 1}",
        "name": str(data["name"]).strip(),
        "district": str(data["district"]).strip(),
        "sanctioned": sanctioned,
        "spent": spent,
        "progress": progress,
    }
    projects.append(new_project)
    save_projects()
    return jsonify({"message": "Project added successfully", "project": analyze_projects()[-1]}), 201


@app.route("/api/projects/<project_id>", methods=["PUT"])
def update_project(project_id):
    project = next((p for p in projects if p["id"] == project_id), None)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    data = request.get_json(silent=True) or {}
    updated = project.copy()

    if "name" in data:
        name = str(data["name"]).strip()
        if not name:
            return jsonify({"error": "Project name cannot be empty"}), 400
        updated["name"] = name

    if "district" in data:
        district = str(data["district"]).strip()
        if not district:
            return jsonify({"error": "District cannot be empty"}), 400
        updated["district"] = district

    amount_unit = str(data.get("amount_unit", "lakh")).strip().lower()
    try:
        if "sanctioned" in data:
            updated["sanctioned"] = _convert_to_lakh(data["sanctioned"], amount_unit)
        if "spent" in data:
            updated["spent"] = _convert_to_lakh(data["spent"], amount_unit)
        if "progress" in data:
            updated["progress"] = int(data["progress"])
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    if updated["sanctioned"] <= 0 or updated["spent"] < 0 or not 0 <= updated["progress"] <= 100:
        return jsonify({"error": "Invalid sanctioned/spent/progress values"}), 400

    if updated["sanctioned"] > MAX_REASONABLE_PROJECT_LAKH or updated["spent"] > MAX_REASONABLE_PROJECT_LAKH:
        return jsonify({"error": "Amount is unusually high. Check the selected money unit."}), 400

    project.update(updated)
    save_projects()
    analysis = calculate_risk(project)
    response_project = project.copy()
    response_project.update({
        "risk_score": analysis["score"],
        "risk_level": analysis["level"],
        "risk_reasons": analysis["reasons"],
    })
    return jsonify({"message": "Project updated successfully", "project": response_project})


@app.route("/api/projects/<project_id>", methods=["DELETE"])
def delete_project(project_id):
    project = next((p for p in projects if p["id"] == project_id), None)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    projects.remove(project)
    save_projects()
    return jsonify({"message": "Project deleted successfully"})


@app.route("/api/dashboard")
def dashboard_data():
    analyzed_projects = analyze_projects()
    total_projects = len(analyzed_projects)
    completed = sum(1 for p in analyzed_projects if p["progress"] >= 90)
    delayed = sum(1 for p in analyzed_projects if p["progress"] < 70)
    ongoing = total_projects - completed - delayed
    high_risk = sum(1 for p in analyzed_projects if p["risk_level"] == "High")
    medium_risk = sum(1 for p in analyzed_projects if p["risk_level"] == "Medium")
    low_risk = sum(1 for p in analyzed_projects if p["risk_level"] == "Low")
    total_sanctioned = sum(p["sanctioned"] for p in analyzed_projects)
    total_spent = sum(p["spent"] for p in analyzed_projects)

    district_funds = {}
    for p in analyzed_projects:
        district = p["district"]
        district_funds.setdefault(district, {"sanctioned": 0, "spent": 0})
        district_funds[district]["sanctioned"] += p["sanctioned"]
        district_funds[district]["spent"] += p["spent"]

    return jsonify({
        "total_projects": total_projects,
        "completed": completed,
        "ongoing": ongoing,
        "delayed": delayed,
        "high_risk": high_risk,
        "medium_risk": medium_risk,
        "low_risk": low_risk,
        "total_sanctioned": total_sanctioned,
        "total_spent": total_spent,
        "district_funds": district_funds,
    })


@app.route("/api/alerts")
def get_alerts():
    alerts = []
    for project in projects:
        analysis = calculate_risk(project)
        if analysis["score"] >= 40:
            alert = project.copy()
            alert["risk_score"] = analysis["score"]
            alert["risk_level"] = analysis["level"]
            alert["reasons"] = analysis["reasons"]
            alerts.append(alert)
    return jsonify(alerts)

# =========================================================
# REPORT APIS
# =========================================================

@app.route("/api/reports", methods=["GET"])
def get_reports():
    report_type = request.args.get("type", "").strip()
    district = request.args.get("district", "").strip()
    date_from_raw = request.args.get("from", "").strip()
    date_to_raw = request.args.get("to", "").strip()
    date_from = parse_iso_date(date_from_raw)
    date_to = parse_iso_date(date_to_raw)

    if date_from_raw and date_from is None:
        return jsonify({"error": "Invalid Date From value"}), 400
    if date_to_raw and date_to is None:
        return jsonify({"error": "Invalid Date To value"}), 400
    if date_from and date_to and date_from > date_to:
        return jsonify({"error": "Date From cannot be after Date To"}), 400

    filtered = list(reports)
    if report_type:
        filtered = [r for r in filtered if r["type"] == report_type]
    if district:
        filtered = [r for r in filtered if r["district"] == district]
    if date_from:
        filtered = [r for r in filtered if datetime.fromisoformat(r["generated_at"]).date() >= date_from]
    if date_to:
        filtered = [r for r in filtered if datetime.fromisoformat(r["generated_at"]).date() <= date_to]

    filtered.sort(key=lambda r: r["generated_at"], reverse=True)
    return jsonify(filtered)


@app.route("/api/reports/stats", methods=["GET"])
def report_stats():
    ordered = sorted(reports, key=lambda r: r["generated_at"], reverse=True)
    now = datetime.now()
    this_month = sum(
        1 for r in reports
        if datetime.fromisoformat(r["generated_at"]).year == now.year
        and datetime.fromisoformat(r["generated_at"]).month == now.month
    )
    latest = ordered[0] if ordered else None
    return jsonify({
        "total_reports": len(reports),
        "this_month": this_month,
        "downloads": sum(r.get("download_count", 0) for r in reports),
        "last_report_text": relative_time_text(latest["generated_at"]) if latest else "No reports",
        "last_report_name": latest["name"] if latest else "",
        "scheduled": SCHEDULED_REPORTS,
    })


@app.route("/api/reports/generate", methods=["POST"])
def generate_report_api():
    data = request.get_json(silent=True) or {}
    report_type = str(data.get("type", "Summary")).strip()
    district = str(data.get("district", "Rajasthan")).strip()
    custom_name = str(data.get("name", "")).strip()

    if report_type not in REPORT_TYPES:
        return jsonify({"error": "Unsupported report type"}), 400
    if district not in VALID_DISTRICTS:
        return jsonify({"error": "Unsupported district"}), 400
    if len(custom_name) > 80:
        return jsonify({"error": "Report name is too long"}), 400

    next_number = max([int(r["id"].split("-")[-1]) for r in reports] + [1000]) + 1
    name = custom_name or REPORT_NAME_BY_TYPE[report_type]
    report = {
        "id": f"RPT-{next_number}",
        "name": name,
        "type": report_type,
        "district": district,
        "generated_at": datetime.now().replace(microsecond=0).isoformat(),
        "size": "1.5 MB",
        "download_count": 0,
    }
    reports.append(report)
    save_reports()
    return jsonify({"message": "Report generated successfully", "report": report_payload(report)}), 201


@app.route("/api/reports/<report_id>", methods=["GET"])
def get_report(report_id):
    report = find_report(report_id)
    if not report:
        return jsonify({"error": "Report not found"}), 404
    return jsonify(report_payload(report))


@app.route("/api/reports/<report_id>", methods=["DELETE"])
def delete_report_api(report_id):
    report = find_report(report_id)
    if not report:
        return jsonify({"error": "Report not found"}), 404
    reports.remove(report)
    save_reports()
    return jsonify({"message": "Report deleted successfully"})


@app.route("/api/reports/<report_id>/download", methods=["GET"])
def download_report_api(report_id):
    report = find_report(report_id)
    if not report:
        return jsonify({"error": "Report not found"}), 404

    selected = get_report_projects(report["district"])
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["MPLADS AI Monitor Report"])
    writer.writerow(["Report Name", report["name"]])
    writer.writerow(["Report Type", report["type"]])
    writer.writerow(["District", report["district"]])
    writer.writerow(["Generated On", report["generated_at"]])
    writer.writerow([])
    writer.writerow(["Project ID", "Project", "District", "Sanctioned (Lakh)", "Spent (Lakh)", "Progress (%)", "Risk Score", "Risk Level", "Risk Indicators"])
    for project in selected:
        writer.writerow([
            project["id"],
            project["name"],
            project["district"],
            project["sanctioned"],
            project["spent"],
            project["progress"],
            project["risk_score"],
            project["risk_level"],
            "; ".join(project["risk_reasons"]) or "No major risk indicator",
        ])

    report["download_count"] = report.get("download_count", 0) + 1
    save_reports()
    content = output.getvalue().encode("utf-8-sig")
    stream = BytesIO(content)
    safe_name = "-".join(report["name"].lower().split())
    return send_file(
        stream,
        mimetype="text/csv; charset=utf-8",
        as_attachment=True,
        download_name=f"{safe_name}.csv",
    )

# =========================================================
# SERVE FRONTEND FILES
# =========================================================

@app.route("/<path:filename>")
def serve_frontend(filename):
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), filename)

# =========================================================
# START SERVER
# =========================================================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5002")), debug=True)
