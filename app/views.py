import os
import fitz
from fpdf import FPDF
import calendar
from datetime import datetime
from flask import Blueprint, render_template, request, send_file, current_app
import re

main = Blueprint('main', __name__)

def extract_absences_from_text(text):
    lines = text.splitlines()
    name_index = lines.index("Name")
    present_index = lines.index("Present")
    emp_name = " ".join(lines[name_index + 1:present_index]).strip()

    match = re.search(r"[A-Za-z]+-\d{4}", text)
    if not match:
        raise ValueError("Could not extract month and year.")
    month_clean = match.group(0)
    today = datetime.strptime(month_clean, "%B-%Y")

    status_index = lines.index("Status")
    status_values = lines[status_index + 1:status_index + 32]

    absent_days = []
    sunday_days = []
    for i, status in enumerate(status_values):
        day_date = i + 1
        try:
            weekday = datetime(today.year, today.month, day_date).strftime("%A")
        except ValueError:
            continue
        if weekday == "Sunday":
            sunday_days.append((day_date, f"{day_date}", weekday))
        elif status == "A":
            absent_days.append((day_date, f"{day_date}", weekday))

    return emp_name, month_clean, absent_days, sunday_days

@main.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files['report_pdf']
        if file and file.filename.endswith('.pdf'):
            upload_folder = os.path.join(current_app.root_path, "static/uploads")
            os.makedirs(upload_folder, exist_ok=True)
            file_path = os.path.join(upload_folder, file.filename)
            file.save(file_path)

            with fitz.open(file_path) as doc:
                text = "".join([p.get_text() for p in doc])

            emp_name, month, absent_days, sunday_days = extract_absences_from_text(text)
            return render_template("leave_form.html", emp_name=emp_name, month=month, absent_days=absent_days, sunday_days=sunday_days)
    return render_template("upload.html")

@main.route('/submit', methods=['POST'])
def submit():
    emp_name = request.form.get("emp_name")
    month = request.form.get("month")
    num_rows = int(request.form.get("num_rows"))
    advance = float(request.form.get("advance", 0))

    salary_map = {
        "Akshay Tinkar": 32000,
        "Anil Soni": 18000,
        "Yash": 15000,
        "Amit Kumar": 28000
    }

    base_salary = salary_map.get(emp_name.strip(), 0)
    per_day_salary = round(base_salary / 30)
    paid_leaves = 1

    # Non-Sunday absences
    adjusted_absents = []
    reasons = []
    issue_days = []

    for i in range(num_rows):
        date = request.form.get(f"date_{i}")
        day = request.form.get(f"day_{i}")
        reason = request.form.get(f"reason_{i}")
        issue = request.form.get(f"issue_{i}")
        if date and reason:
            adjusted_absents.append((i + 1, date, day, reason))
            if issue:
                issue_days.append(date)

    # Sunday work entries
    sunday_days = []
    sunday_reasons = []
    i = 0
    while True:
        date = request.form.get(f"sunday_date_{i}")
        day = request.form.get(f"sunday_day_{i}")
        reason = request.form.get(f"sunday_reason_{i}")
        if not date:
            break
        sunday_days.append((i + 1, date, day))
        sunday_reasons.append(reason if reason else "")
        i += 1

    working_sundays = sum(1 for r in sunday_reasons if r.strip())
    total_leaves = len(adjusted_absents)
    deduction_days = total_leaves - paid_leaves - working_sundays - len(issue_days)
    deduction_days = max(deduction_days, 0)
    deduction_amount = deduction_days * per_day_salary
    final_salary = base_salary - deduction_amount - advance

    file_name = f"{emp_name.replace(' ', '_')}_{month}_LeaveReport.pdf"
    output_path = os.path.join(current_app.root_path, "static", file_name)

    generate_pdf(
        emp_name, month, adjusted_absents, [r[3] for r in adjusted_absents],
        sunday_days, sunday_reasons, output_path,
        base_salary, per_day_salary, deduction_amount, advance, final_salary, issue_days
    )

    return send_file(output_path, as_attachment=True)

def generate_pdf(emp_name, month, absent_days, reasons, sunday_days, sunday_reasons, output_path,
                 base_salary, per_day_salary, deduction_amount, advance, final_salary, issue_days):
    pdf = FPDF()
    pdf.add_page()

    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Digital Sun Media", ln=True, align="C")
    pdf.cell(0, 10, "Leave Report", ln=True, align="C")
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"Name: {emp_name}", ln=True)
    pdf.cell(0, 10, f"Month: {month}", ln=True)
    pdf.ln(5)

    # Absence Table
    pdf.set_font("Arial", "B", 12)
    pdf.cell(20, 10, "S.No", 1)
    pdf.cell(30, 10, "Date", 1)
    pdf.cell(25, 10, "Day", 1)
    pdf.cell(85, 10, "Reason", 1)
    pdf.cell(30, 10, "Issue?", 1)
    pdf.ln()
    pdf.set_font("Arial", "", 12)
    for i, (sno, date, day, reason) in enumerate(absent_days):
        pdf.cell(20, 10, str(i + 1), 1)
        pdf.cell(30, 10, date, 1)
        pdf.cell(25, 10, day, 1)
        pdf.cell(85, 10, reason, 1)
        pdf.cell(30, 10, "Yes" if date in issue_days else "", 1)

        pdf.ln()

    # Sunday Table
    if any(r.strip() for r in sunday_reasons):
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "Sunday Work Report", ln=True, align="C")
        pdf.ln(5)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(20, 10, "S.No", 1)
        pdf.cell(40, 10, "Date", 1)
        pdf.cell(40, 10, "Day", 1)
        pdf.cell(90, 10, "Reason", 1)
        pdf.ln()
        pdf.set_font("Arial", "", 12)
        for i, (sno, date, day) in enumerate(sunday_days):
            reason = sunday_reasons[i]
            pdf.cell(20, 10, str(i + 1), 1)
            pdf.cell(40, 10, date, 1)
            pdf.cell(40, 10, day, 1)
            pdf.cell(90, 10, reason, 1)
            pdf.ln()

    # Salary Summary
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Approximate Salary Calculation Summary", ln=True, align="C")
    pdf.ln(5)
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"Base Salary: Rs. {base_salary}", ln=True)
    pdf.cell(0, 10, f"Per Day Salary: Rs. {per_day_salary}", ln=True)
    pdf.cell(0, 10, f"Total Leaves: {len(absent_days)}", ln=True)
    pdf.cell(0, 10, f"Issue Reported Days: {len(issue_days)}", ln=True)
    pdf.cell(0, 10, f"Paid Leave (Office Provided): 1", ln=True)
    pdf.cell(0, 10, f"Working Sundays: {sum(1 for r in sunday_reasons if r.strip())}", ln=True)
    pdf.cell(0, 10, f"Leave Days Counted for Deduction: {max(len(absent_days) - 1 - sum(1 for r in sunday_reasons if r.strip()) - len(issue_days), 0)}", ln=True)
    pdf.cell(0, 10, f"Deduction Amount: Rs. {deduction_amount}", ln=True)
    pdf.cell(0, 10, f"Advance Received: Rs. {advance}", ln=True)
    pdf.cell(0, 10, f"Final Salary to be Paid: Rs. {final_salary}", ln=True)

    # Add red-colored note
    pdf.ln(5)
    pdf.set_text_color(255, 0, 0)  # Set text color to red
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 10, "Note: This salary calculation is only approximate, actual salary may differ because of Sandwich Sundays.", ln=True)
    pdf.set_text_color(0, 0, 0)  # Reset to black after the note

    pdf.output(output_path)
