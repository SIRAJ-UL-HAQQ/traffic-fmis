# routes/payment.py — Payment Processing
from flask import (Blueprint, render_template, request,
                   redirect, url_for, flash, session)
from routes.auth import login_required
from db import get_db
from utils.business_logic import calculate_total_due
import uuid

payment_bp = Blueprint('payment', __name__)


@payment_bp.route('/challan/<int:challan_id>', methods=['GET', 'POST'])
@login_required
def pay_challan(challan_id):
    conn   = get_db()
    cursor = conn.cursor(dictionary=True)

    # Load full challan details
    cursor.execute(
        """SELECT c.challan_id, c.challan_number, c.issue_date, c.due_date,
                  c.total_amount, c.paid_amount, c.status,
                  v.violation_date, v.location,
                  vt.type_name,
                  veh.registration_number,
                  o.full_name as owner_name, o.phone as owner_phone
           FROM Challans c
           JOIN Violations v    ON c.violation_id = v.violation_id
           JOIN Violation_Types vt ON v.type_id = vt.type_id
           JOIN Vehicles veh    ON v.vehicle_id = veh.vehicle_id
           JOIN Owners o        ON veh.owner_id = o.owner_id
           WHERE c.challan_id = %s""",
        (challan_id,)
    )
    challan = cursor.fetchone()

    if not challan:
        flash('Challan not found.', 'danger')
        return redirect(url_for('officer.dashboard'))

    if challan['status'] == 'paid':
        flash('This challan is already fully paid.', 'info')
        return redirect(url_for('officer.view_challan', challan_id=challan_id))

    if challan['status'] == 'cancelled':
        flash('This challan has been cancelled.', 'warning')
        return redirect(url_for('officer.view_challan', challan_id=challan_id))

    due_info = calculate_total_due(challan_id, conn)

    if request.method == 'POST':
        amount_str = request.form.get('amount', '').strip()
        method     = request.form.get('method', 'cash')

        try:
            amount = float(amount_str)
            if amount <= 0:
                raise ValueError('Must be positive')
        except (ValueError, TypeError):
            flash('Please enter a valid payment amount.', 'danger')
            return render_template('payment/pay_challan.html',
                                   challan=challan, due_info=due_info)

        if amount > due_info['amount_due'] + 0.01:  # small tolerance for floats
            flash(f"Amount cannot exceed outstanding balance of PKR {due_info['amount_due']:,.2f}.", 'warning')
            return render_template('payment/pay_challan.html',
                                   challan=challan, due_info=due_info)

        receipt_number = f"RCP-{uuid.uuid4().hex[:8].upper()}"
        officer_id     = session.get('officer_id')

        cursor.execute(
            """INSERT INTO Payments
               (challan_id, amount_paid, payment_method, receipt_number, processed_by)
               VALUES (%s, %s, %s, %s, %s)""",
            (challan_id, amount, method, receipt_number, officer_id)
        )

        # Update paid_amount and status
        new_paid_amount = float(challan['paid_amount']) + amount
        # Make sure ALL challan money fields are cast:
        total_amount    = float(challan['total_amount'])
        paid_amount     = float(challan['paid_amount'])
        new_paid_amount = paid_amount + amount
        total_due_full  = float(challan['total_amount']) + due_info['penalty']

        if new_paid_amount >= total_due_full - 0.01:
            new_status = 'paid'
        else:
            new_status = 'partial'

        cursor.execute(
            "UPDATE Challans SET paid_amount = %s, status = %s WHERE challan_id = %s",
            (new_paid_amount, new_status, challan_id)
        )
        conn.commit()

        flash(
            f"✅ Payment of PKR {amount:,.2f} recorded! Receipt No: {receipt_number}",
            'success'
        )
        return redirect(url_for('officer.view_challan', challan_id=challan_id))

    return render_template('payment/pay_challan.html',
                           challan=challan,
                           due_info=due_info)
