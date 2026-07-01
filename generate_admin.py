"""
generate_admin.py — Helper script to create the admin user directly in the database.

Run this ONCE after setting up your database:
    python generate_admin.py

It will:
  1. Ask for a password (or use the default "Admin@123")
  2. Hash it securely with Werkzeug
  3. Insert the admin user into the database
"""

from werkzeug.security import generate_password_hash
import mysql.connector
import getpass
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ── Database settings (must match your config.py / .env) ──
DB_CONFIG = {
    'host':     os.environ.get('MYSQL_HOST', 'localhost'),
    'user':     os.environ.get('MYSQL_USER', 'root'),
    'password': os.environ.get('MYSQL_PASSWORD', ''),
    'database': os.environ.get('MYSQL_DB', 'traffic_db'),
}

def main():
    print("=" * 50)
    print("  Traffic FMIS — Admin Account Setup")
    print("=" * 50)

    username = input("Admin username [admin]: ").strip() or 'admin'
    email    = input("Admin email [admin@traffic.gov.pk]: ").strip() or 'admin@traffic.gov.pk'
    password = getpass.getpass("Admin password [Admin@123]: ") or 'Admin@123'

    if len(password) < 6:
        print("❌ Password must be at least 6 characters.")
        return

    password_hash = generate_password_hash(password)
    print(f"\n✅ Hash generated: {password_hash[:40]}...")

    try:
        conn   = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Delete existing admin with same username if any
        cursor.execute("DELETE FROM Users WHERE username = %s", (username,))

        # Insert fresh admin user
        cursor.execute(
            """INSERT INTO Users (username, password_hash, role, email)
               VALUES (%s, %s, 'admin', %s)""",
            (username, password_hash, email)
        )
        conn.commit()
        print(f"\n✅ Admin user '{username}' created successfully!")
        print(f"   Email:    {email}")
        print(f"   Password: {password}")
        print(f"\n   👉 Login at: http://127.0.0.1:5000/login")
        conn.close()

    except mysql.connector.Error as e:
        print(f"\n❌ Database error: {e}")
        print("   Make sure MySQL is running and DB_CONFIG is correct in this script.")

if __name__ == '__main__':
    main()
