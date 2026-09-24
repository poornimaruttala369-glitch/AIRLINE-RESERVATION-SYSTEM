"""
✈️ AIRLINE RESERVATION SYSTEM
Flask Application Entry Point & Factory
---------------------------------------
Academic Context:
- Flask Framework (Python Web Development)
- MVC Architectural Pattern (Controllers via Blueprints)
- Context Processors & Global Branding
- Role-based Authorization & Error Handling
"""
import os
import sys
from flask import Flask, render_template, session, redirect, url_for, g

from config import config_by_name
from database.db import init_database, get_db_cursor
from routes.auth_helpers import get_current_user
from routes.auth import auth_bp
from routes.flights import flights_bp
from routes.booking import booking_bp
from routes.admin import admin_bp


def create_app(config_name=None):
    """
    Application Factory Pattern.
    Creates and configures an instance of the Flask application.
    """
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')

    app = Flask(__name__)
    config_obj = config_by_name.get(config_name, config_by_name['default'])
    app.config.from_object(config_obj)

    # Ensure database is initialized with tables and sample data
    try:
        init_database()
    except Exception as e:
        print(f"[STARTUP WARNING] DB initialization notice: {e}")

    # Register Flask Blueprints (Controllers)
    app.register_blueprint(auth_bp)
    app.register_blueprint(flights_bp)
    app.register_blueprint(booking_bp)
    app.register_blueprint(admin_bp)

    # Global context processor for branding and session user across all templates
    @app.context_processor
    def inject_global_context():
        user = get_current_user()
        return {
            'app_name': config_obj.APP_NAME,
            'app_tagline': config_obj.APP_TAGLINE,
            'current_user': user
        }

    # Public Routes
    @app.route('/')
    def index():
        """Home page with hero search and Why Choose Us cards."""
        try:
            with get_db_cursor() as cur:
                cur.execute("SELECT * FROM airports ORDER BY city ASC")
                airports = cur.fetchall()
        except Exception as e:
            print(f"[HOME ERROR] Failed to fetch airports: {e}")
            airports = []
        return render_template('index.html', airports=airports)

    @app.route('/about')
    def about():
        """Academic Architecture and Project Information."""
        return render_template('about.html')

    @app.route('/health')
    def health():
        """System health probe."""
        return {
            'status': 'healthy',
            'app': config_obj.APP_NAME,
            'tagline': config_obj.APP_TAGLINE
        }

    # Error Handlers (Section 27: Friendly error pages, no exposed stack traces)
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('errors/500.html'), 500

    return app


app = create_app()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'True').lower() in ('true', '1', 't')
    print(f"[AIRLINE SYSTEM] Starting Airline Reservation System on http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=debug)
