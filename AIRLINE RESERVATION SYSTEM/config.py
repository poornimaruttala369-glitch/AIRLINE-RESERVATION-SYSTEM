"""
Application Configuration Module
--------------------------------
Demonstrates OOPJ concepts: Class inheritance and Encapsulation.
Loads environment variables safely using python-dotenv.
"""
import os
from dotenv import load_dotenv

# Load .env file if present
load_dotenv()


class Config:
    """Base Configuration class."""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev_default_secret_key_airline_sys_2026')
    
    # Database Settings
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = int(os.getenv('DB_PORT', 3306))
    DB_NAME = os.getenv('DB_NAME', 'airline_reservation_db')
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')

    # Overbooking Policy Defaults
    DEFAULT_OVERBOOKING_PERCENTAGE = float(os.getenv('DEFAULT_OVERBOOKING_PERCENTAGE', 5.0))

    # Branding & App Meta
    APP_NAME = "AIRLINE RESERVATION SYSTEM"
    APP_TAGLINE = "Fly Smart. Book Easy. Travel Confidently."

    @classmethod
    def get_db_config(cls):
        """Encapsulated helper to return dictionary of MySQL connection params."""
        return {
            'host': cls.DB_HOST,
            'port': cls.DB_PORT,
            'user': cls.DB_USER,
            'password': cls.DB_PASSWORD,
            'database': cls.DB_NAME,
            'cursorclass': None,  # Will be configured per query requirement
            'autocommit': False,  # Strict ACID transactions
        }


class DevelopmentConfig(Config):
    """Development Environment Configuration."""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """Production Environment Configuration."""
    DEBUG = False
    TESTING = False


# Map environment names to configuration classes
config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
