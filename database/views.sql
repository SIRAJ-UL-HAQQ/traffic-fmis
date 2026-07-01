USE traffic_db;

-- View 1: Complete challan summary (used for reports)
CREATE OR REPLACE VIEW vw_challan_summary AS
SELECT
    c.challan_number,
    c.status,
    c.total_amount,
    c.paid_amount,
    c.total_amount - c.paid_amount AS balance_due,
    c.due_date,
    veh.registration_number,
    o.full_name AS owner_name,
    o.cnic,
    vt.type_name AS violation_type,
    vt.severity,
    v.violation_date,
    v.location,
    off.full_name AS officer_name,
    off.badge_number
FROM Challans c
JOIN Violations v       ON c.violation_id  = v.violation_id
JOIN Violation_Types vt ON v.type_id       = vt.type_id
JOIN Vehicles veh       ON v.vehicle_id    = veh.vehicle_id
JOIN Owners o           ON veh.owner_id    = o.owner_id
JOIN Officers off       ON v.officer_id    = off.officer_id;

-- View 2: Repeat offenders (vehicles with 3+ violations)
CREATE OR REPLACE VIEW vw_repeat_offenders AS
SELECT
    veh.registration_number,
    o.full_name AS owner_name,
    o.cnic,
    o.phone,
    COUNT(*) AS total_violations,
    SUM(v.fine_amount) AS total_fines,
    MAX(v.violation_date) AS last_violation_date
FROM Violations v
JOIN Vehicles veh ON v.vehicle_id = veh.vehicle_id
JOIN Owners o     ON veh.owner_id = o.owner_id
GROUP BY v.vehicle_id
HAVING total_violations >= 3
ORDER BY total_violations DESC;

-- View 3: Monthly revenue summary
CREATE OR REPLACE VIEW vw_monthly_revenue AS
SELECT
    DATE_FORMAT(payment_date, '%Y-%m') AS month,
    COUNT(*) AS total_payments,
    SUM(amount_paid) AS total_collected,
    AVG(amount_paid) AS avg_payment
FROM Payments
GROUP BY month
ORDER BY month DESC;