# 🚦 Traffic FMIS — Traffic Violation & Fine Management System

A web application for managing traffic violations, fines (challans), and payments, built with **Flask** and **MySQL**. It supports two roles — **Admin** and **Traffic Officer** — with role-based dashboards, vehicle/owner registration, violation recording with automatic repeat-offender penalty calculation, PDF challan generation, and payment processing.

## Features

- **Role-based access** — separate Admin and Officer dashboards with session-based auth
- **Vehicle & owner registration** — linked by CNIC, with unique registration numbers
- **Violation recording** — officers log violations against a configurable list of violation types
- **Automatic fine calculation** — repeat offenses on the same vehicle are multiplied (1st: 1.0x, 2nd: 1.25x, 3rd: 1.5x, 4th+: 2.0x)
- **Challan (ticket) generation** — auto-numbered challans with due dates
- **PDF challan export** — formatted PDF generated with ReportLab
- **Payments** — record and track full/partial payments against challans
- **Universal search** — look up by vehicle registration number or owner CNIC
- **Admin reports** — revenue and repeat-offender views backed by SQL views
- **Custom error pages** — 404 / 500

## Tech Stack

| Layer      | Technology |
|------------|------------|
| Backend    | Python 3, Flask 3 |
| Database   | MySQL 8 (via `mysql-connector-python`) |
| PDF export | ReportLab |
| Frontend   | Jinja2 templates, vanilla CSS/JS, Chart.js |
| Auth       | Werkzeug password hashing, Flask sessions |

## Project Structure

```
traffic_fmis/
├── app.py                  # App entry point, blueprint registration
├── config.py                # Configuration (reads from environment variables)
├── db.py                    # MySQL connection management
├── generate_admin.py        # CLI script to create the first admin user
├── requirements.txt
├── .env.example              # Template for local environment variables
├── database/
│   ├── schema.sql           # Table definitions (3NF)
│   ├── seed_data.sql        # Sample data
│   └── views.sql            # Reporting views (revenue, repeat offenders, etc.)
├── routes/                   # Flask blueprints
│   ├── auth.py               # Login/logout/register, access-control decorators
│   ├── officer.py            # Officer dashboard, record violation, register vehicle
│   ├── admin.py               # Admin dashboard, officer & violation-type management, reports
│   ├── payment.py             # Payment processing
│   └── search.py              # Vehicle/owner search
├── utils/
│   ├── business_logic.py      # Fine calculation, challan number generation
│   └── pdf_generator.py       # PDF challan builder
├── templates/                 # Jinja2 templates (admin/, officer/, payment/, search/, errors/)
└── static/                    # CSS and JS
```

### Database schema

Core tables: `Users`, `Officers`, `Owners`, `Vehicles`, `Violation_Types`, `Violations`, `Challans`, `Payments`.

Reporting views: `vw_challan_summary`, `vw_repeat_offenders`, `vw_monthly_revenue`.

## Getting Started

### Prerequisites

- Python 3.10+
- MySQL 8.x (server running locally or remotely)

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd traffic_fmis
```

### 2. Create a virtual environment and install dependencies

```bash
python -m venv venv
source venv/bin/activate      # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure environment variables

Copy the example file and fill in your own values:

```bash
cp .env.example .env
```

Edit `.env`:

```
SECRET_KEY=some-long-random-string
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=your-mysql-password
MYSQL_DB=traffic_db
MYSQL_PORT=3306
```

> `.env` is git-ignored — it will never be committed. `config.py` reads all values from environment variables at runtime.

### 4. Set up the database

```bash
mysql -u root -p < database/schema.sql
mysql -u root -p < database/views.sql
mysql -u root -p < database/seed_data.sql   # optional sample data
```

### 5. Create an admin account

```bash
python generate_admin.py
```

Follow the prompts to set a username, email, and password.

### 6. Run the app

```bash
python app.py
```

Visit **http://127.0.0.1:5000** and log in with the admin account you created.

## Security Notes

- Passwords are hashed with Werkzeug (`generate_password_hash` / `check_password_hash`) — never stored in plain text.
- Database credentials and the Flask secret key are read from environment variables, not hardcoded, and `.env` is excluded from version control via `.gitignore`.
- Sessions expire after 30 minutes of inactivity.
- Before deploying this publicly, set `debug=False` in `app.py` and use a strong, unique `SECRET_KEY`.

## License

Add a license of your choice (e.g. MIT) — none is currently specified.
