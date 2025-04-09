
import calendar
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, send_file
import fitz  # PyMuPDF
from fpdf import FPDF
import os

main = Blueprint('main', __name__)
UPLOAD_FOLDER = 'app/static/uploads'

@main.route('/', methods=['GET'])
def index():
    return render_template('upload.html')

@main.route('/upload', methods=['POST'])
def upload():
    uploaded_file = request.files['report_pdf']
    if uploaded_file.filename.endswith('.pdf'):
        file_path = os.path.join(UPLOAD_FOLDER, uploaded_file.filename)
        uploaded_file.save(file_path)
        with fitz.open(file_path) as doc:
            text = ""
            for page in doc:
                text += page.get_text()
        name_line = [line for line in text.splitlines() if "Name" in line][0]
        emp_name = name_line.split("Name")[1].split("Present")[0].strip()
        month_line = [line for line in text.splitlines() if "Report Month" in line][0]
        month = month_line.split("Report Month")[1].strip()
        status_line = [line for line in text.splitlines() if "Status" in line][0]
        status_values = status_line.replace("Status", "").strip().split()
        days_line = [line for line in text.splitlines() if line.strip().startswith("1")][0]
        days = days_line.strip().split()
        today = datetime.strptime(month, "%B-%Y")
        absent_days = [(i+1, days[i], calendar.day_name[datetime(today.year, today.month, i+1).weekday()])
                       for i, val in enumerate(status_values) if val == "A"]
        return render_template("leave_form.html", emp_name=emp_name, month=month,
                               absent_days=absent_days)
    return redirect('/')

@main.route('/submit-leave', methods=['POST'])
def submit_leave():
    emp_name = request.form.get("emp_name")
    month = request.form.get("month")
    num_rows = int(request.form.get("num_rows"))
    rows = []
    for i in range(num_rows):
        date = request.form.get(f"date_{i}")
        day = request.form.get(f"day_{i}")
        reason = request.form.get(f"reason_{i}")
        rows.append((i+1, date, day, reason))
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
    for row in rows:
        pdf.cell(20, 10, str(row[0]), 1)
        pdf.cell(40, 10, row[1], 1)
        pdf.cell(40, 10, row[2], 1)
        pdf.cell(90, 10, row[3], 1)
        pdf.ln()
    output_path = "app/static/leave_report.pdf"
    pdf.output(output_path)
    return send_file(output_path, as_attachment=True)
