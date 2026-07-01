# app.py — Main Flask Application Entry Point
from flask import Flask, redirect, url_for, render_template
from config import Config
from db import close_db

app = Flask(__name__)
app.config.from_object(Config)

# Register teardown so DB connection closes after each request
app.teardown_appcontext(close_db)

# Import and register blueprints
from routes.auth    import auth_bp
from routes.officer import officer_bp
from routes.admin   import admin_bp
from routes.payment import payment_bp
from routes.search  import search_bp

app.register_blueprint(auth_bp)
app.register_blueprint(officer_bp, url_prefix='/officer')
app.register_blueprint(admin_bp,   url_prefix='/admin')
app.register_blueprint(payment_bp, url_prefix='/payment')
app.register_blueprint(search_bp,  url_prefix='/search')


# ── Root redirect ──
@app.route('/')
def index():
    return redirect(url_for('auth.login'))


# ── Error Handlers ──
@app.errorhandler(404)
def not_found(e):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('errors/500.html'), 500


if __name__ == '__main__':
    app.run(debug=True)