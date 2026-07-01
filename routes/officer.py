# routes/officer.py — Officer Dashboard, Record Violation, Register Vehicle, View Challan
from flask import (Blueprint, render_template, request,
                   redirect, url_for, session, flash, send_file)
from routes.auth import login_required
from db import get_db
from utils.business_logic import calculate_fine, generate_challan_number
from utils.pdf_generator import generate_challan_pdf
from datetime import datetime, timedelta

officer_bp = Blueprint('officer', __name__)


# ─────────────────────────────────────────────
#  Officer Dashboard
# ─────────────────────────────────────────────

@officer_bp.route('/dashboard')
@login_required
def dashboard():
    conn      = get_db()
    cursor    = conn.cursor(dictionary=True)
    officer_id = session.get('officer_id')

    # Stats for this officer
    cursor.execute(
        "SELECT COUNT(*) as total FROM Violations WHERE officer_id = %s",
        (officer_id,)
    )
    total_violations = cursor.fetchone()['total']

    cursor.execute(
        """SELECT COUNT(*) as total FROM Challans c
           JOIN Violations v ON c.violation_id = v.violation_id
           WHERE v.officer_id = %s AND c.status = 'pending'""",
        (officer_id,)
    )
    pending_challans = cursor.fetchone()['total']

    cursor.execute(
        """SELECT COALESCE(SUM(c.paid_amount), 0) as total
           FROM Challans c JOIN Violations v ON c.violation_id = v.violation_id
           WHERE v.officer_id = %s""",
        (officer_id,)
    )
    fines_collected = cursor.fetchone()['total']

    # Recent 10 violations by this officer
    cursor.execute(
        """SELECT v.violation_id, v.violation_date, v.location, v.fine_amount,
                  vt.type_name, veh.registration_number,
                  o.full_name as owner_name,
                  c.challan_id, c.challan_number, c.status
           FROM Violations v
           JOIN Violation_Types vt ON v.type_id = vt.type_id
           JOIN Vehicles veh       ON v.vehicle_id = veh.vehicle_id
           JOIN Owners o           ON veh.owner_id = o.owner_id
           LEFT JOIN Challans c    ON v.violation_id = c.violation_id
           WHERE v.officer_id = %s
           ORDER BY v.violation_date DESC
           LIMIT 10""",
        (officer_id,)
    )
    recent = cursor.fetchall()

    return render_template('officer/dashboard.html',
                           total_violations=total_violations,
                           pending_challans=pending_challans,
                           fines_collected=fines_collected,
                           recent=recent)


# ─────────────────────────────────────────────
#  Register Vehicle + Owner
# ─────────────────────────────────────────────
@officer_bp.route('/register-vehicle', methods=['GET', 'POST'])
@login_required
def register_vehicle():
    conn   = get_db()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        form = request.form

        # --- Owner ---
        cnic = form.get('cnic', '').strip()
        if not cnic:
            flash('Owner CNIC is required.', 'danger')
            return render_template('officer/register_vehicle.html')

        cursor.execute("SELECT owner_id FROM Owners WHERE cnic = %s", (cnic,))
        existing = cursor.fetchone()

        if existing:
            owner_id = existing['owner_id']
        else:
            if not form.get('owner_name', '').strip():
                flash('Owner name is required for new owner.', 'danger')
                return render_template('officer/register_vehicle.html')
            cursor.execute(
                """INSERT INTO Owners (cnic, full_name, address, phone, email)
                   VALUES (%s, %s, %s, %s, %s)""",
                (cnic, form.get('owner_name', '').strip(),
                 form.get('address', ''),
                 form.get('phone', ''),
                 form.get('owner_email', ''))
            )
            owner_id = cursor.lastrowid

        # --- Vehicle ---
        reg_number = form.get('reg_number', '').strip().upper()
        if not reg_number:
            flash('Registration number is required.', 'danger')
            return render_template('officer/register_vehicle.html')

        # Check if already registered BEFORE trying to insert
        cursor.execute(
            "SELECT vehicle_id FROM Vehicles WHERE registration_number = %s",
            (reg_number,)
        )
        if cursor.fetchone():
            flash(f'Vehicle {reg_number} is already registered.', 'warning')
            return render_template('officer/register_vehicle.html')

        # Insert vehicle safely
        try:
            cursor.execute(
                """INSERT INTO Vehicles
                   (owner_id, registration_number, make, model, year, color, vehicle_type)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (owner_id, reg_number,
                 form.get('make', ''), form.get('model', ''),
                 form.get('year') or None,
                 form.get('color', ''),
                 form.get('vehicle_type', 'car'))
            )
            conn.commit()
            flash(f'Vehicle {reg_number} registered successfully!', 'success')
            return redirect(url_for('officer.record_violation'))

        except Exception as e:
            conn.rollback()
            if 'Duplicate entry' in str(e):
                flash(f'Vehicle {reg_number} is already registered.', 'danger')
            else:
                flash(f'Error registering vehicle: {str(e)}', 'danger')
            return render_template('officer/register_vehicle.html')

    return render_template('officer/register_vehicle.html')


# ─────────────────────────────────────────────
#  Record Violation
# ─────────────────────────────────────────────

@officer_bp.route('/record-violation', methods=['GET', 'POST'])
@login_required
def record_violation():
    conn      = get_db()
    cursor    = conn.cursor(dictionary=True)
    officer_id = session.get('officer_id')

    if request.method == 'POST':
        vehicle_id  = request.form.get('vehicle_id')
        type_id     = request.form.get('type_id')
        location    = request.form.get('location', '').strip()
        description = request.form.get('description', '').strip()
        viol_date   = request.form.get('violation_date', '')

        if not all([vehicle_id, type_id, location, viol_date]):
            flash('Vehicle, violation type, location, and date are all required.', 'danger')
        else:
            # Calculate fine (includes repeat-offender logic)
            fine_amount, multiplier = calculate_fine(int(type_id), int(vehicle_id), conn)

            # Insert violation
            cursor.execute(
                """INSERT INTO Violations
                   (vehicle_id, officer_id, type_id, violation_date, location, description, fine_amount)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (vehicle_id, officer_id, type_id,
                 viol_date, location, description, fine_amount)
            )
            violation_id = cursor.lastrowid

            # Auto-generate challan
            challan_number = generate_challan_number(conn)
            due_date       = datetime.now() + timedelta(days=15)

            cursor.execute(
                """INSERT INTO Challans
                   (challan_number, violation_id, due_date, total_amount)
                   VALUES (%s, %s, %s, %s)""",
                (challan_number, violation_id, due_date, fine_amount)
            )
            challan_id = cursor.lastrowid
            conn.commit()

            if multiplier > 1.0:
                flash(f'⚠ Repeat offender detected! Fine multiplied by {multiplier}x.', 'warning')
            flash(f'Violation recorded. Challan {challan_number} generated.', 'success')
            return redirect(url_for('officer.view_challan', challan_id=challan_id))

    # Load dropdowns
    cursor.execute(
        """SELECT v.vehicle_id, v.registration_number, v.make, v.model,
                  o.full_name as owner_name
           FROM Vehicles v JOIN Owners o ON v.owner_id = o.owner_id
           ORDER BY v.registration_number"""
    )
    vehicles = cursor.fetchall()

    cursor.execute(
        "SELECT type_id, type_name, base_fine, severity FROM Violation_Types WHERE is_active = 1 ORDER BY type_name"
    )
    violation_types = cursor.fetchall()

    return render_template('officer/record_violation.html',
                           vehicles=vehicles,
                           violation_types=violation_types,
                           today=datetime.now().strftime('%Y-%m-%dT%H:%M'))


# ─────────────────────────────────────────────
#  View Challan
# ─────────────────────────────────────────────

@officer_bp.route('/challan/<int:challan_id>')
@login_required
def view_challan(challan_id):
    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    officer_id = session.get('officer_id')

    cursor.execute(
        """SELECT c.challan_id, c.challan_number, c.issue_date, c.due_date,
                  c.total_amount, c.paid_amount, c.status,
                  v.violation_date, v.location, v.description, v.fine_amount,
                  vt.type_name, vt.severity,
                  veh.registration_number, veh.make, veh.model, veh.color, veh.year,
                  o.full_name as owner_name, o.cnic, o.phone as owner_phone,
                  off.full_name as officer_name, off.badge_number
           FROM Challans c
           JOIN Violations v    ON c.violation_id = v.violation_id
           JOIN Violation_Types vt ON v.type_id = vt.type_id
           JOIN Vehicles veh    ON v.vehicle_id = veh.vehicle_id
           JOIN Owners o        ON veh.owner_id = o.owner_id
           JOIN Officers off    ON v.officer_id = off.officer_id
           WHERE c.challan_id = %s""",
        (challan_id,)
    )
    challan = cursor.fetchone()
    
    if not challan:
        flash('Challan not found.', 'danger')
        return redirect(url_for('officer.dashboard'))

    
    if session.get('role') != 'admin' and challan:
        cursor.execute(
            """SELECT 1 FROM Violations v
               JOIN Challans c ON v.violation_id = c.violation_id
               WHERE c.challan_id = %s AND v.officer_id = %s""",
            (challan_id, officer_id)
        )
        if not cursor.fetchone():
            flash('You do not have permission to view this challan.', 'danger')
            return redirect(url_for('officer.dashboard'))

    
    # Fetch payments for this challan
    cursor.execute(
        """SELECT p.payment_id, p.amount_paid, p.payment_date,
                  p.payment_method, p.receipt_number,
                  off.full_name as processed_by_name
           FROM Payments p
           LEFT JOIN Officers off ON p.processed_by = off.officer_id
           WHERE p.challan_id = %s
           ORDER BY p.payment_date DESC""",
        (challan_id,)
    )
    payments = cursor.fetchall()

    # Calculate if overdue
    from utils.business_logic import calculate_total_due
    due_info = calculate_total_due(challan_id, conn)
    
    # Determine where the back button should go
    referrer = request.referrer or ''
    if 'all_challans' in referrer or 'admin' in referrer:
        back_url = url_for('admin.all_challans')
    elif 'search' in referrer:
        back_url = url_for('search.search')
    else:
        back_url = url_for('officer.dashboard')

    return render_template('officer/view_challan.html',
                           challan=challan,
                           payments=payments,
                           due_info=due_info,
                           back_url=back_url)


# ─────────────────────────────────────────────
#  Download PDF Challan
# ─────────────────────────────────────────────

@officer_bp.route('/challan/<int:challan_id>/pdf')
@login_required
def download_pdf(challan_id):
    conn   = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        """SELECT c.challan_number, c.issue_date, c.due_date,
                  c.total_amount, c.paid_amount, c.status,
                  v.violation_date, v.location, v.fine_amount,
                  vt.type_name,
                  veh.registration_number,
                  CONCAT(veh.make, ' ', veh.model, ' (', veh.color, ')') as vehicle_model,
                  o.full_name as owner_name, o.cnic as owner_cnic,
                  off.full_name as officer_name, off.badge_number
           FROM Challans c
           JOIN Violations v    ON c.violation_id = v.violation_id
           JOIN Violation_Types vt ON v.type_id = vt.type_id
           JOIN Vehicles veh    ON v.vehicle_id = veh.vehicle_id
           JOIN Owners o        ON veh.owner_id = o.owner_id
           JOIN Officers off    ON v.officer_id = off.officer_id
           WHERE c.challan_id = %s""",
        (challan_id,)
    )
    data = cursor.fetchone()

    if not data:
        flash('Challan not found.', 'danger')
        return redirect(url_for('officer.dashboard'))

    from utils.business_logic import calculate_total_due
    due_info = calculate_total_due(challan_id, conn)

    challan_data = {
        'challan_number': data['challan_number'],
        'issue_date':     str(data['issue_date'])[:10],
        'due_date':       str(data['due_date'])[:10],
        'vehicle_reg':    data['registration_number'],
        'vehicle_model':  data['vehicle_model'],
        'owner_name':     data['owner_name'],
        'owner_cnic':     data['owner_cnic'],
        'violation_type': data['type_name'],
        'violation_date': str(data['violation_date'])[:16],
        'location':       data['location'],
        'fine_amount':    float(data['fine_amount']),
        'penalty':        due_info['penalty'],
        'total_due':      due_info['amount_due'] + due_info['paid_amount'],
        'officer_name':   data['officer_name'],
        'badge_number':   data['badge_number'],
    }

    pdf_buffer = generate_challan_pdf(challan_data)
    filename   = f"Challan_{data['challan_number']}.pdf"

    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )
