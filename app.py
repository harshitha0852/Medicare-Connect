import os
import sqlite3
from datetime import datetime
from flask import Flask, flash, jsonify, redirect, render_template, request, url_for

BASE = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__)
app.config.update(SECRET_KEY=os.environ.get('SECRET_KEY', 'local-demo-only-change-me'), DATABASE=os.path.join(BASE, 'medicare.db'))
DEPARTMENTS = ('General Medicine', 'Cardiology', 'Dermatology', 'Orthopedics', 'Pediatrics')
DOCTORS = {'General Medicine': 'Dr. Ananya Rao', 'Cardiology': 'Dr. Vivek Shah', 'Dermatology': 'Dr. Meera Nair', 'Orthopedics': 'Dr. Arjun Kumar', 'Pediatrics': 'Dr. Sara Thomas'}
SYMPTOMS = ('fever', 'cough', 'headache', 'rash', 'joint pain', 'chest pain', 'breathing difficulty', 'unconscious', 'severe bleeding')


def db():
    connection = sqlite3.connect(app.config['DATABASE'])
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with db() as con:
        con.executescript('''CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT, patient TEXT NOT NULL, email TEXT NOT NULL,
            phone TEXT NOT NULL, age INTEGER NOT NULL, department TEXT NOT NULL,
            doctor TEXT NOT NULL, appointment_date TEXT NOT NULL, appointment_time TEXT NOT NULL,
            symptoms TEXT NOT NULL, priority TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'Scheduled',
            created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS triage_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, symptoms TEXT NOT NULL, priority TEXT NOT NULL,
            recommendation TEXT NOT NULL, created_at TEXT NOT NULL);''')


def triage(symptoms):
    value = symptoms.strip().lower()
    if not value:
        raise ValueError('Please describe symptoms.')
    if any(term in value for term in ('chest pain', 'breathing difficulty', 'unconscious', 'severe bleeding')):
        return 'Emergency', 'Seek emergency medical care immediately. Do not wait for an online appointment.'
    if any(term in value for term in ('high fever', 'persistent vomiting', 'severe headache')):
        return 'High', 'Contact a qualified clinician promptly for an urgent assessment.'
    if any(term in value for term in ('fever', 'cough', 'headache', 'rash', 'joint pain')):
        return 'Medium', 'Arrange a medical consultation for assessment.'
    return 'Low', 'Book a routine consultation if symptoms persist or concern you.'


def validate_appointment(form):
    patient = form.get('patient', '').strip()
    email = form.get('email', '').strip()
    phone = form.get('phone', '').strip()
    symptoms = form.get('symptoms', '').strip()
    department = form.get('department', '')
    date = form.get('appointment_date', '')
    time = form.get('appointment_time', '')
    if len(patient) < 2:
        raise ValueError('Enter a valid patient name.')
    if '@' not in email or '.' not in email.split('@')[-1]:
        raise ValueError('Enter a valid email address.')
    if not phone.isdigit() or len(phone) != 10:
        raise ValueError('Enter a 10-digit phone number.')
    try:
        age = int(form.get('age', ''))
    except (TypeError, ValueError):
        raise ValueError('Enter a valid age.') from None
    if not 1 <= age <= 120:
        raise ValueError('Age must be between 1 and 120.')
    if department not in DEPARTMENTS:
        raise ValueError('Select a valid department.')
    try:
        day = datetime.strptime(date, '%Y-%m-%d').date()
        datetime.strptime(time, '%H:%M')
    except ValueError:
        raise ValueError('Enter a valid appointment date and time.') from None
    if day < datetime.now().date():
        raise ValueError('Appointment date cannot be in the past.')
    priority, _ = triage(symptoms)
    return patient, email, phone, age, department, DOCTORS[department], date, time, symptoms, priority


@app.get('/')
def home():
    return render_template('home.html')


@app.route('/triage', methods=['GET', 'POST'])
def triage_page():
    result = None
    symptoms = ''
    if request.method == 'POST':
        symptoms = request.form.get('symptoms', '')
        try:
            result = triage(symptoms)
            with db() as con:
                con.execute('INSERT INTO triage_logs (symptoms,priority,recommendation,created_at) VALUES (?,?,?,?)', (symptoms, *result, datetime.now().isoformat(timespec='seconds')))
        except ValueError as exc:
            flash(str(exc), 'error')
    return render_template('triage.html', result=result, symptoms=symptoms)


@app.route('/appointments/new', methods=['GET', 'POST'])
def new_appointment():
    if request.method == 'POST':
        try:
            values = validate_appointment(request.form)
            with db() as con:
                con.execute('''INSERT INTO appointments
                    (patient,email,phone,age,department,doctor,appointment_date,appointment_time,symptoms,priority,created_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?)''', (*values, datetime.now().isoformat(timespec='seconds')))
            flash('Appointment booked successfully!', 'success')
            return redirect(url_for('appointments'))
        except ValueError as exc:
            flash(str(exc), 'error')
    return render_template('book.html', departments=DEPARTMENTS, doctors=DOCTORS)


@app.get('/appointments')
def appointments():
    status = request.args.get('status', '')
    priority = request.args.get('priority', '')
    query = 'SELECT * FROM appointments WHERE 1=1'
    args = []
    if status in ('Scheduled', 'Completed', 'Cancelled'):
        query += ' AND status=?'
        args.append(status)
    if priority in ('Low', 'Medium', 'High', 'Emergency'):
        query += ' AND priority=?'
        args.append(priority)
    query += ' ORDER BY appointment_date, appointment_time, id'
    with db() as con:
        rows = con.execute(query, args).fetchall()
    return render_template('appointments.html', appointments=rows, status=status, priority=priority)


@app.get('/appointments/<int:appointment_id>')
def appointment_detail(appointment_id):
    with db() as con:
        row = con.execute('SELECT * FROM appointments WHERE id=?', (appointment_id,)).fetchone()
    if row is None:
        return render_template('not_found.html'), 404
    return render_template('detail.html', item=row)


@app.post('/appointments/<int:appointment_id>/status')
def update_status(appointment_id):
    status = request.form.get('status', '')
    if status not in ('Scheduled', 'Completed', 'Cancelled'):
        flash('Invalid appointment status.', 'error')
        return redirect(url_for('appointments'))
    with db() as con:
        cur = con.execute('UPDATE appointments SET status=? WHERE id=?', (status, appointment_id))
    if not cur.rowcount:
        return render_template('not_found.html'), 404
    flash('Appointment status updated.', 'success')
    return redirect(url_for('appointments'))


@app.get('/dashboard')
def dashboard():
    with db() as con:
        total = con.execute('SELECT COUNT(*) FROM appointments').fetchone()[0]
        scheduled = con.execute("SELECT COUNT(*) FROM appointments WHERE status='Scheduled'").fetchone()[0]
        emergency = con.execute("SELECT COUNT(*) FROM appointments WHERE priority='Emergency'").fetchone()[0]
        triages = con.execute('SELECT COUNT(*) FROM triage_logs').fetchone()[0]
        departments = con.execute('SELECT department, COUNT(*) AS count FROM appointments GROUP BY department ORDER BY count DESC').fetchall()
    return render_template('dashboard.html', total=total, scheduled=scheduled, emergency=emergency, triages=triages, departments=departments)


@app.get('/api/health')
def health():
    return jsonify(status='ok', service='MediCare Connect')


@app.get('/api/metrics')
def metrics():
    with db() as con:
        appointments_count = con.execute('SELECT COUNT(*) FROM appointments').fetchone()[0]
        triage_count = con.execute('SELECT COUNT(*) FROM triage_logs').fetchone()[0]
    return jsonify(appointments=appointments_count, triage_assessments=triage_count)


@app.post('/api/triage')
def api_triage():
    payload = request.get_json(silent=True) or {}
    try:
        priority, recommendation = triage(str(payload.get('symptoms', '')))
        return jsonify(priority=priority, recommendation=recommendation)
    except ValueError as exc:
        return jsonify(error=str(exc)), 400


@app.errorhandler(404)
def not_found(_):
    return render_template('not_found.html'), 404


init_db()

if __name__ == '__main__':
    app.run(debug=True)
