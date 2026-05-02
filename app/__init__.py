import os
from flask import Flask
from app.models import db
from app.routes import register_routes

def create_app():
    # Initialize the Flask application
    app = Flask(__name__)

    # Configure the SQLite database
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'dse_scanner.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Bind the SQLAlchemy instance to this specific app
    db.init_app(app)

    # Register all our web routes
    register_routes(app)

    return app