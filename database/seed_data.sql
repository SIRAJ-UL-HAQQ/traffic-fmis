-- ================================================================
-- Traffic FMIS — Seed Data
-- Run AFTER schema.sql:
--   mysql -u root -p traffic_db < database/seed_data.sql
-- ================================================================

USE traffic_db;

-- ────────────────────────────────────────────
--  Violation Types (10 common violations)
-- ────────────────────────────────────────────
INSERT INTO Violation_Types (type_name, description, base_fine, severity) VALUES
('Over Speeding',          'Vehicle exceeding posted speed limit',              3000.00, 'moderate'),
('Red Light Jump',         'Vehicle crossing red traffic signal',               5000.00, 'major'),
('Wrong Side Driving',     'Driving on incorrect side of road',                 4000.00, 'major'),
('No Helmet',              'Motorcyclist not wearing helmet',                   1000.00, 'minor'),
('Mobile Phone Use',       'Using handheld phone while driving',                2000.00, 'minor'),
('Drunk Driving',          'Driving under influence of alcohol or drugs',      25000.00, 'critical'),
('No Seatbelt',            'Driver or passenger not wearing seatbelt',          1500.00, 'minor'),
('Illegal Parking',        'Vehicle parked in a prohibited or tow-away zone',   2000.00, 'moderate'),
('Overloading',            'Vehicle carrying excess load or passengers',         5000.00, 'major'),
('Expired Registration',   'Vehicle registration documents expired',             3000.00, 'moderate')
ON DUPLICATE KEY UPDATE type_name = type_name;  -- Safe re-run

-- ────────────────────────────────────────────
--  Default Admin User
--  Username: admin
--  Password: Admin@123
--
--  IMPORTANT: Generate a fresh hash by running:
--    python generate_admin.py
--  Then replace the hash below with the output.
-- ────────────────────────────────────────────

-- This hash is for password "Admin@123" — generated with Werkzeug
-- You MUST regenerate this using generate_admin.py before use!
INSERT INTO Users (username, password_hash, role, email)
VALUES (
    'admin',
    'pbkdf2:sha256:260000$PLACEHOLDER_RUN_generate_admin_py',
    'admin',
    'admin@traffic.gov.pk'
)
ON DUPLICATE KEY UPDATE username = username;
