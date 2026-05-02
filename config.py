import os

# Gets the absolute path of your current directory
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    # A secret key is required by Flask to secure user sessions for your Admin panel
    SECRET_KEY = 'super-secret-trading-key'
    
    # Tells SQLAlchemy exactly where to create your SQLite database file
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'app.db')
    
    # Turns off a feature we don't need to save memory
    SQLALCHEMY_TRACK_MODIFICATIONS = False