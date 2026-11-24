# P01 — MediCare Connect

Flask + SQLite academic demonstration of a hospital appointment and symptom-triage platform.

## Run (Windows PowerShell, VS Code)

```powershell
cd "C:\Users\ronit\OneDrive\New folder\MediCare_Connect_P01"
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

Open http://127.0.0.1:5000 . Stop server with Ctrl+C.

## Automated tests (new terminal)

```powershell
.\.venv\Scripts\python.exe -m pytest -v
.\.venv\Scripts\python.exe -m pytest --cov=app --cov-report=html --cov-report=term-missing
start .\htmlcov\index.html
```

All 25 tests use a temporary SQLite database. Running tests will not overwrite the normal app database.

## Features
- Landing page, responsive design
- Appointment creation, input validation, appointment details and status updates
- Department/doctor mapping and appointment filtering
- Rule-based symptom priority assessment: Low, Medium, High, Emergency
- Dashboard, health API, metrics API, triage API
- SQLite persistence and GitHub Actions test workflow

## Important limitations
- This is an educational demo, not a real hospital platform.
- The triage logic is rule-based, not trained machine learning and not medical advice.
- No patient authentication, role-based access, production security hardening, real doctor availability checks, SMS, email, payment, or hospital integration.
- Do not enter real patient information; use synthetic sample data.
- The default Flask development server is for local use only.
