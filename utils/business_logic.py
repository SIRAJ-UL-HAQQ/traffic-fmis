# utils/business_logic.py — Fine Calculation, Challan Generation, Penalty Logic
from datetime import datetime


def calculate_fine(type_id: int, vehicle_id: int, conn) -> tuple:
    """
    Calculate the final fine for a violation.

    Repeat-offender multiplier rules:
      1st offense of this type on this vehicle  → 1.0x
      2nd offense                               → 1.25x
      3rd offense                               → 1.5x
      4th offense and beyond                    → 2.0x

    Returns:
        (final_fine: float, multiplier: float)
    """
    cursor = conn.cursor(dictionary=True)

    # Get base fine from Violation_Types
    cursor.execute(
        "SELECT base_fine FROM Violation_Types WHERE type_id = %s",
        (type_id,)
    )
    vt = cursor.fetchone()
    if not vt:
        return 0.0, 1.0

    base_fine = float(vt['base_fine'])

    # Count past violations of this exact type for this vehicle
    cursor.execute(
        """SELECT COUNT(*) as cnt
           FROM Violations
           WHERE vehicle_id = %s AND type_id = %s""",
        (vehicle_id, type_id)
    )
    past_count = cursor.fetchone()['cnt']

    if past_count == 0:
        multiplier = 1.0
    elif past_count == 1:
        multiplier = 1.25
    elif past_count == 2:
        multiplier = 1.5
    else:
        multiplier = 2.0

    final_fine = round(base_fine * multiplier, 2)
    return final_fine, multiplier


def calculate_total_due(challan_id: int, conn) -> dict:
    """
    Calculate the total amount due, including any late penalty.

    Late penalty: 10% of original amount per week overdue, capped at 50%.
    Formula: penalty = total_amount * min(0.1 * weeks_overdue, 0.5)

    Returns dict with:
        total_amount, penalty, paid_amount, amount_due, is_overdue, weeks_overdue
    """
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT total_amount, paid_amount, due_date, status FROM Challans WHERE challan_id = %s",
        (challan_id,)
    )
    challan = cursor.fetchone()

    if not challan:
        return {'total_amount': 0, 'penalty': 0, 'paid_amount': 0, 'amount_due': 0,
                'is_overdue': False, 'weeks_overdue': 0}

    total   = float(challan['total_amount'])
    paid    = float(challan['paid_amount'])
    due     = challan['due_date']
    now     = datetime.now()

    # due_date may come from MySQL as datetime or date — normalise
    if hasattr(due, 'date'):
        pass  # it's already a datetime
    else:
        due = datetime.combine(due, datetime.min.time())

    penalty      = 0.0
    is_overdue   = False
    weeks_overdue = 0

    if now > due and challan['status'] not in ('paid', 'cancelled'):
        is_overdue    = True
        weeks_overdue = (now - due).days / 7
        penalty_rate  = min(0.1 * weeks_overdue, 0.5)
        penalty       = round(total * penalty_rate, 2)

    amount_due = max(0.0, total + penalty - paid)

    return {
        'total_amount': total,
        'penalty':      penalty,
        'paid_amount':  paid,
        'amount_due':   round(amount_due, 2),
        'is_overdue':   is_overdue,
        'weeks_overdue': round(weeks_overdue, 1),
    }


def generate_challan_number(conn) -> str:
    """Use MAX(challan_id) not COUNT — safe even if rows were deleted."""
    from datetime import datetime
    year   = datetime.now().year
    cursor = conn.cursor()
    cursor.execute("SELECT COALESCE(MAX(challan_id), 0) FROM Challans")
    max_id = cursor.fetchone()[0]
    seq    = max_id + 1
    return f"TRF-{year}-{seq:06d}"