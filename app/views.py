import os
import fitz
from fpdf import FPDF
import calendar
from datetime import datetime
from flask import Blueprint, render_template, request, send_file
import re

main = Blueprint('main', __name__)

def extract_absences_from_text(text):
    lines = text.splitlines()
    name_index = lines.index("Name")
    present_index = lines.index("Present")
    emp_name = " ".join(lines[name_index + 1:present_index]).strip()

    match = re.search(r"[A-Za-z]+-\d{4}", text)
    month_clean = match.group(0)
    today = datetime.strptime(month_clean, "%B-%Y")

    status_index = lines.index("Status")
    status_values = lines[status_index + 1:status_index + 32]
    day_start_index = lines.index("1")
    days = lines[day_start_index:day_start_index + 31]

    absent_days = []
    for i, status in enumerate(status_values):
        if status == "A":
            day_num = days[i]
            day_name = calendar.day_name[datetime(today.year, today.month, i+1).weekday()]
            absent_days.append((i+1, day_num, day_name))

    return emp_name, month_clean, absent_days

def generate_pdf(emp_name, month, absent_days, reasons, output_path):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Digital Sun Media", ln=True, align="C")
    pdf.cell(0, 10, "Leave Report", ln=True, align="C")
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"Name: {emp_name}", ln=True)
    pdf.cell(0, 10, f"Month: {month}", ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(20, 10, "S.No", 1)
    pdf.cell(40, 10, "Date", 1)
    pdf.cell(40, 10, "Day", 1)
    pdf.cell(90, 10, "Reason", 1)
    pdf.ln()
    pdf.set_font("Arial", "", 12)
    for i, (date, day, reason) in enumerate(zip([d[1] for d in absent_days], [d[2] for d in absent_days], reasons)):
        pdf.cell(20, 10, str(i+1), 1)
        pdf.cell(40, 10, date, 1)
        pdf.cell(40, 10, day, 1)
        pdf.cell(90, 10, reason, 1)
        pdf.ln()
    pdf.output(output_path)

@main.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files['report_pdf']
        if file and file.filename.endswith('.pdf'):
            upload_folder = "app/static/uploads"
            os.makedirs(upload_folder, exist_ok=True)  # ✅ Ensures folder exists even on fresh deploy
            path = os.path.join(upload_folder, file.filename)
            file.save(path)
            with fitz.open(path) as doc:
                text = "".join([p.get_text() for p in doc])
            emp_name, month, absent_days = extract_absences_from_text(text)
            return render_template("leave_form.html", emp_name=emp_name, month=month, absent_days=absent_days)
    return render_template("upload.html")

@main.route('/submit', methods=['POST'])
def submit():
    emp_name = request.form.get("emp_name")
    month = request.form.get("month")
    num_rows = int(request.form.get("num_rows"))
    absent_days = []
    reasons = []
    for i in range(num_rows):
        date = request.form.get(f"date_{i}")
        day = request.form.get(f"day_{i}")
        reason = request.form.get(f"reason_{i}")
        absent_days.append((i+1, date, day))
        reasons.append(reason)

    file_name = f"{emp_name.replace(' ', '_')}_{month}_LeaveReport.pdf"
    output_path = os.path.join("app/static", file_name)
    generate_pdf(emp_name, month, absent_days, reasons, output_path)
    return send_file(output_path, as_attachment=True)
