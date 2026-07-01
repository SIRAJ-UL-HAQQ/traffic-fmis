# routes/search.py — Universal Search Module
from flask import Blueprint, render_template, request
from routes.auth import login_required
from db import get_db

search_bp = Blueprint('search', __name__)


@search_bp.route('/', methods=['GET', 'POST'])
@login_required
def search():
    conn    = get_db()
    cursor  = conn.cursor(dictionary=True)
    results = []
    searched = False

    if request.method == 'POST':
        searched = True
        reg_number = request.form.get('reg_number', '').strip()
        owner_cnic = request.form.get('owner_cnic', '').strip()
        challan_no = request.form.get('challan_no', '').strip()
        date_from  = request.form.get('date_from', '').strip()
        date_to    = request.form.get('date_to', '').strip()
        officer_name = request.form.get('officer_name', '').strip()
        status_filter = request.form.get('status', '').strip()

        query = """
            SELECT c.challan_id, c.challan_number, c.issue_date, c.due_date,
                   c.total_amount, c.paid_amount, c.status,
                   v.violation_date, v.location,
                   vt.type_name, vt.severity,
                   veh.registration_number, veh.make, veh.model,
                   o.full_name as owner_name, o.cnic,
                   off.full_name as officer_name, off.badge_number
            FROM Challans c
            JOIN Violations v    ON c.violation_id = v.violation_id
            JOIN Violation_Types vt ON v.type_id = vt.type_id
            JOIN Vehicles veh    ON v.vehicle_id = veh.vehicle_id
            JOIN Owners o        ON veh.owner_id = o.owner_id
            JOIN Officers off    ON v.officer_id = off.officer_id
            WHERE 1=1
        """
        params = []

        if reg_number:
            query += " AND veh.registration_number LIKE %s"
            params.append(f"%{reg_number}%")

        if owner_cnic:
            query += " AND o.cnic LIKE %s"
            params.append(f"%{owner_cnic}%")

        if challan_no:
            query += " AND c.challan_number LIKE %s"
            params.append(f"%{challan_no}%")

        if date_from:
            query += " AND v.violation_date >= %s"
            params.append(date_from)

        if date_to:
            query += " AND v.violation_date <= %s"
            params.append(f"{date_to} 23:59:59")

        if officer_name:
            query += " AND off.full_name LIKE %s"
            params.append(f"%{officer_name}%")

        if status_filter in ['pending', 'partial', 'paid', 'cancelled']:
            query += " AND c.status = %s"
            params.append(status_filter)

        query += " ORDER BY v.violation_date DESC LIMIT 100"
        cursor.execute(query, params)
        results = cursor.fetchall()

    return render_template('search/search.html',
                           results=results,
                           searched=searched)
