# db.py — MySQL Database Connection Manager
import mysql.connector
from flask import current_app, g

def get_db():
    """
    Get (or create) a MySQL connection stored on Flask's 'g' object.
    'g' is request-scoped — a fresh connection per request.
    """
    if 'db' not in g:
        g.db = mysql.connector.connect(
            host=current_app.config['MYSQL_HOST'],
            user=current_app.config['MYSQL_USER'],
            password=current_app.config['MYSQL_PASSWORD'],
            database=current_app.config['MYSQL_DB'],
            port=current_app.config.get('MYSQL_PORT', 3306),
            autocommit=False
        )
    return g.db

def close_db(e=None):
    """Close DB connection at end of request (registered in app.py)."""
    db = g.pop('db', None)
    if db is not None:
        db.close()
