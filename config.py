# config.py — Application Configuration
import os
from datetime import timedelta

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv is optional; env vars can also be set directly

class Config:
    # CHANGE THIS to a long random string in production!
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-only-change-me')

    # MySQL Database Settings — configure via environment variables (see .env.example)
    MYSQL_HOST     = os.environ.get('MYSQL_HOST', 'localhost')
    MYSQL_USER     = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')
    MYSQL_DB       = os.environ.get('MYSQL_DB', 'traffic_db')
    MYSQL_PORT     = int(os.environ.get('MYSQL_PORT', 3306))

    # Session expires after 30 minutes of inactivity
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
