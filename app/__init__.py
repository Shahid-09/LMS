from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_session import Session
from flask_mail import Mail
from datetime import timedelta

db = SQLAlchemy()
mail = Mail()  # Initialize Flask-Mail

def create_app():
    app = Flask(__name__)

    app.config.from_object("config.Config")  # Load configurations from config file

    # Set session configuration
    app.config['SESSION_TYPE'] = 'filesystem'  # Use server-side sessions
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=120)  # Set session timeout

    # Email Configuration
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USE_SSL'] = False
    app.config['MAIL_USERNAME'] = 'factsnappy@gmail.com'
    app.config['MAIL_PASSWORD'] = 'xxvniqvsbknphgdx'
    app.config['MAIL_DEFAULT_SENDER'] = 'factsnappy@gmail.com'
    
    Session(app)  
    db.init_app(app)  
    mail.init_app(app)  # Initialize Flask-Mail with the app

    # Blueprint for auth routes
    from .auth.auth import auth
    app.register_blueprint(auth)

    # Blueprint for main routes
    from .main.main import main
    app.register_blueprint(main)

    return app
