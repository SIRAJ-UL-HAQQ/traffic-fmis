# routes/admin.py — Admin Dashboard, Officers List, Violation Types Management
from flask import (Blueprint, render_template, request,
                   redirect, url_for, flash, session)
from routes.auth import login_required, admin_required
from db import get_db

admin_bp = Blueprint('admin', __name__)


# ─────────────────────────────────────────────
#  Admin Dashboard (Analytics)
# ─────────────────────────────────────────────

@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    conn   = get_db()
    cursor = conn.cursor(dictionary=True)

    # ── KPI Stats ──
    cursor.execute("SELECT COUNT(*) as total FROM Violations")
    total_violations = cursor.fetchone()['total']

    cursor.execute("SELECT COALESCE(SUM(paid_amount), 0) as total FROM Challans")
    total_collected = float(cursor.fetchone()['total'])

    cursor.execute("SELECT COUNT(*) as total FROM Challans WHERE status = 'pending'")
    pending_challans = cursor.fetchone()['total']

    cursor.execute(
        """SELECT COUNT(*) as total FROM Officers o
           JOIN Users u ON o.user_id = u.user_id WHERE u.is_active = 1"""
    )
    active_officers = cursor.fetchone()['total']

    cursor.execute(
        "SELECT COALESCE(SUM(total_amount - paid_amount), 0) as total FROM Challans WHERE status != 'paid'"
    )
    outstanding = float(cursor.fetchone()['total'])

    # ── Monthly data (last 6 months) for Chart.js ──
    cursor.execute(
        """SELECT DATE_FORMAT(violation_date, '%Y-%m') as month,
                  COUNT(*) as count,
                  SUM(fine_amount) as total_fines
           FROM Violations
           WHERE violation_date >= DATE_SUB(NOW(), INTERVAL 6 MONTH)
           GROUP BY month
           ORDER BY month"""
    )
    monthly_data = cursor.fetchall()

    # ── Top 5 violation types ──
    cursor.execute(
        """SELECT vt.type_name, COUNT(*) as cnt
           FROM Violations v
           JOIN Violation_Types vt ON v.type_id = vt.type_id
           GROUP BY vt.type_id
           ORDER BY cnt DESC
           LIMIT 5"""
    )
    top_violations = cursor.fetchall()

    # ── Repeat offenders (3+ violations) ──
    cursor.execute(
        """SELECT veh.registration_number, o.full_name as owner_name,
                  COUNT(*) as offense_count,
                  SUM(v.fine_amount) as total_fines,
                  MAX(v.violation_date) as last_violation
           FROM Violations v
           JOIN Vehicles veh ON v.vehicle_id = veh.vehicle_id
           JOIN Owners o     ON veh.owner_id = o.owner_id
           GROUP BY v.vehicle_id
           HAVING offense_count >= 3
           ORDER BY offense_count DESC
           LIMIT 10"""
    )
    repeat_offenders = cursor.fetchall()

    # ── Recent violations (all officers) ──
    cursor.execute(
        """SELECT v.violation_id, v.violation_date, v.location, v.fine_amount,
                  vt.type_name, veh.registration_number,
                  o.full_name as owner_name,
                  off.full_name as officer_name,
                  c.challan_number, c.status
           FROM Violations v
           JOIN Violation_Types vt ON v.type_id = vt.type_id
           JOIN Vehicles veh       ON v.vehicle_id = veh.vehicle_id
           JOIN Owners o           ON veh.owner_id = o.owner_id
           JOIN Officers off       ON v.officer_id = off.officer_id
           LEFT JOIN Challans c    ON v.violation_id = c.violation_id
           ORDER BY v.violation_date DESC
           LIMIT 15"""
    )
    recent_violations = cursor.fetchall()

    return render_template('admin/dashboard.html',
                           total_violations=total_violations,
                           total_collected=total_collected,
                           pending_challans=pending_challans,
                           active_officers=active_officers,
                           outstanding=outstanding,
                           monthly_data=monthly_data,
                           top_violations=top_violations,
                           repeat_offenders=repeat_offenders,
                           recent_violations=recent_violations)


# ─────────────────────────────────────────────
#  Officers Management
# ─────────────────────────────────────────────

@admin_bp.route('/officers')
@login_required
@admin_required
def officers():
    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """SELECT o.officer_id, o.badge_number, o.full_name, o.department,
                  o.phone, o.precinct, o.hire_date,
                  u.username, u.email, u.is_active, u.last_login,
                  (SELECT COUNT(*) FROM Violations v2 WHERE v2.officer_id = o.officer_id) as violation_count
           FROM Officers o
           JOIN Users u ON o.user_id = u.user_id
           ORDER BY o.full_name"""
    )
    officers_list = cursor.fetchall()
    return render_template('admin/officers.html', officers=officers_list)


@admin_bp.route('/officers/<int:officer_id>/toggle')
@login_required
@admin_required
def toggle_officer(officer_id):
    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT u.user_id, u.is_active FROM Officers o JOIN Users u ON o.user_id=u.user_id WHERE o.officer_id=%s",
        (officer_id,)
    )
    row = cursor.fetchone()
    if row:
        new_status = 0 if row['is_active'] else 1
        cursor.execute("UPDATE Users SET is_active=%s WHERE user_id=%s", (new_status, row['user_id']))
        conn.commit()
        status_text = 'activated' if new_status else 'deactivated'
        flash(f'Officer {status_text} successfully.', 'success')
    return redirect(url_for('admin.officers'))


# ─────────────────────────────────────────────
#  Violation Types Management
# ─────────────────────────────────────────────

@admin_bp.route('/violation-types')
@login_required
@admin_required
def violation_types():
    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Violation_Types ORDER BY severity, type_name")
    vt_list = cursor.fetchall()
    return render_template('admin/violation_types.html', violation_types=vt_list)


@admin_bp.route('/violation-types/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_violation_type():
    if request.method == 'POST':
        form = request.form
        name      = form.get('type_name', '').strip()
        desc      = form.get('description', '').strip()
        base_fine = form.get('base_fine', '0')
        severity  = form.get('severity', 'minor')

        try:
            base_fine = float(base_fine)
            if base_fine <= 0:
                raise ValueError
        except ValueError:
            flash('Base fine must be a positive number.', 'danger')
            return render_template('admin/add_violation_type.html')

        conn   = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO Violation_Types (type_name, description, base_fine, severity) VALUES (%s,%s,%s,%s)",
            (name, desc, base_fine, severity)
        )
        conn.commit()
        flash(f'Violation type "{name}" added.', 'success')
        return redirect(url_for('admin.violation_types'))

    return render_template('admin/add_violation_type.html')


# ─────────────────────────────────────────────
#  All Challans View
# ─────────────────────────────────────────────

@admin_bp.route('/challans')
@login_required
@admin_required
def all_challans():
    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    status_filter = request.args.get('status', '')
    sort_by       = request.args.get('sort', 'issue_date')
    sort_dir      = request.args.get('dir', 'desc')
    
    allowed_sorts = ['issue_date', 'due_date', 'total_amount', 'paid_amount', 'status']
    if sort_by not in allowed_sorts:
        sort_by = 'issue_date'
    if sort_dir not in ['asc', 'desc']:
        sort_dir = 'desc'


    query = """
        SELECT c.challan_id, c.challan_number, c.issue_date, c.due_date,
               c.total_amount, c.paid_amount, c.status,
               veh.registration_number, o.full_name as owner_name,
               vt.type_name, off.full_name as officer_name
        FROM Challans c
        JOIN Violations v    ON c.violation_id = v.violation_id
        JOIN Violation_Types vt ON v.type_id = vt.type_id
        JOIN Vehicles veh    ON v.vehicle_id = veh.vehicle_id
        JOIN Owners o        ON veh.owner_id = o.owner_id
        JOIN Officers off    ON v.officer_id = off.officer_id
    """
    params = []
    if status_filter in ['pending', 'partial', 'paid', 'cancelled']:
        query += " WHERE c.status = %s"
        params.append(status_filter)

    query += f" ORDER BY c.{sort_by} {sort_dir} LIMIT 200"
    cursor.execute(query, params)
    challans = cursor.fetchall()

    return render_template('admin/all_challans.html',
                           challans=challans,
                           status_filter=status_filter,
                           sort_by=sort_by, sort_dir=sort_dir)


@admin_bp.route('/violations/<int:violation_id>/edit', methods=['GET','POST'])
@login_required
@admin_required
def edit_violation(violation_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    if request.method == 'POST':
        new_fine = request.form.get('fine_amount')
        new_location = request.form.get('location')
        new_description = request.form.get('description', '').strip()
        cursor.execute(
            "UPDATE Violations SET fine_amount=%s, location=%s, description=%s WHERE violation_id=%s",
            (new_fine, new_location, new_description, violation_id)
        )
        conn.commit()
        flash('Violation updated successfully.', 'success')
        return redirect(url_for('admin.all_challans'))
    cursor.execute("SELECT * FROM Violations WHERE violation_id=%s", (violation_id,))
    violation = cursor.fetchone()
    return render_template('admin/edit_violation.html', violation=violation)

@admin_bp.route('/challans/<int:challan_id>/cancel')
@login_required
@admin_required
def cancel_challan(challan_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE Challans SET status='cancelled' WHERE challan_id=%s", (challan_id,)
    )
    conn.commit()
    flash('Challan cancelled.', 'success')
    return redirect(url_for('admin.all_challans'))

# Delete officer
@admin_bp.route('/officers/<int:officer_id>/delete')
@login_required
@admin_required
def delete_officer(officer_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT user_id FROM Officers WHERE officer_id=%s", (officer_id,))
    row = cursor.fetchone()
    if row:
        cursor.execute("DELETE FROM Users WHERE user_id=%s", (row['user_id'],))
        conn.commit()
        flash('Officer deleted.', 'success')
    return redirect(url_for('admin.officers'))

# ─────────────────────────────────────────────
#  Edit Officer
# ─────────────────────────────────────────────

@admin_bp.route('/officers/<int:officer_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_officer(officer_id):
    conn   = get_db()
    cursor = conn.cursor(dictionary=True)

    # Load existing officer data
    cursor.execute(
        """SELECT o.officer_id, o.badge_number, o.full_name,
                  o.department, o.phone, o.precinct, o.hire_date,
                  u.email, u.username
           FROM Officers o
           JOIN Users u ON o.user_id = u.user_id
           WHERE o.officer_id = %s""",
        (officer_id,)
    )
    officer = cursor.fetchone()

    if not officer:
        flash('Officer not found.', 'danger')
        return redirect(url_for('admin.officers'))

    if request.method == 'POST':
        full_name  = request.form.get('full_name',  '').strip()
        department = request.form.get('department', '').strip()
        phone      = request.form.get('phone',      '').strip()
        precinct   = request.form.get('precinct',   '').strip()
        email      = request.form.get('email',      '').strip()

        if not full_name:
            flash('Full name is required.', 'danger')
            return render_template('admin/edit_officer.html', officer=officer)

        # UPDATE Officers table
        cursor.execute(
            """UPDATE Officers
               SET full_name=%s, department=%s, phone=%s, precinct=%s
               WHERE officer_id=%s""",
            (full_name, department, phone, precinct, officer_id)
        )

        # UPDATE Users table (email)
        cursor.execute(
            "UPDATE Users SET email=%s WHERE username=%s",
            (email, officer['username'])
        )

        conn.commit()
        flash(f"Officer '{full_name}' updated successfully.", 'success')
        return redirect(url_for('admin.officers'))

    return render_template('admin/edit_officer.html', officer=officer)

# ─────────────────────────────────────────────
#  Reports Page (SQL VIEWs)
# ─────────────────────────────────────────────

@admin_bp.route('/reports')
@login_required
@admin_required
def reports():
    conn   = get_db()
    cursor = conn.cursor(dictionary=True)

    # ── View 1: Challan Summary ──
    cursor.execute(
        """SELECT * FROM vw_challan_summary
           ORDER BY violation_date DESC
           LIMIT 50"""
    )
    challan_summary = cursor.fetchall()

    # ── View 2: Repeat Offenders ──
    cursor.execute("SELECT * FROM vw_repeat_offenders")
    repeat_offenders = cursor.fetchall()

    # ── View 3: Monthly Revenue ──
    cursor.execute("SELECT * FROM vw_monthly_revenue LIMIT 12")
    monthly_revenue = cursor.fetchall()

    # ── Summary totals for top cards ──
    cursor.execute("SELECT COUNT(*) as total FROM vw_challan_summary")
    total_challans = cursor.fetchone()['total']

    cursor.execute(
        "SELECT COALESCE(SUM(total_collected), 0) as total FROM vw_monthly_revenue"
    )
    total_revenue = float(cursor.fetchone()['total'])

    cursor.execute("SELECT COUNT(*) as total FROM vw_repeat_offenders")
    total_repeat = cursor.fetchone()['total']

    cursor.execute(
        "SELECT COUNT(*) as total FROM vw_challan_summary WHERE status = 'pending'"
    )
    total_pending = cursor.fetchone()['total']

    return render_template('admin/reports.html',
                           challan_summary=challan_summary,
                           repeat_offenders=repeat_offenders,
                           monthly_revenue=monthly_revenue,
                           total_challans=total_challans,
                           total_revenue=total_revenue,
                           total_repeat=total_repeat,
                           total_pending=total_pending)

