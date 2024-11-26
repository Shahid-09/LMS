import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your_secret_key')  # This is for Flask sessions and CSRF protection
    # JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'your_jwt_secret_key')  
    
    # PostgreSQL database configuration
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:root@localhost/ledger_db'
