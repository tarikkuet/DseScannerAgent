import os
from flask import Flask
# Import the database instance and models from your models.py file
from app.models import db, Sector, Category, Stock, DailyPerformance, DailyIndicator, WatchlistItem

# Initialize the Flask application
app = Flask(__name__)

# Configure the SQLite database
# This ensures the .db file is created in the same folder as this script
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'dse_scanner.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Bind the SQLAlchemy instance to this specific Flask app
db.init_app(app)

def setup_database():
    """Creates the database tables and populates initial static data."""
    with app.app_context():
        # 1. Create all tables based on the schema in models.py
        db.create_all()
        print("✅ Database tables generated.")

        # 2. Populate DSE Categories (A, B, N, Z)
        dse_categories = ['A', 'B', 'N', 'Z']
        for cat_name in dse_categories:
            # Check if it exists so we don't create duplicates if you run this twice
            if not Category.query.filter_by(name=cat_name).first():
                new_category = Category(name=cat_name)
                db.session.add(new_category)
        
        # 3. Populate Major DSE Sectors
        dse_sectors = [
            'Bank', 'Textile', 'Pharmaceuticals & Chemicals', 
            'Engineering', 'IT Sector', 'Mutual Funds', 
            'Fuel & Power', 'Financial Institutions', 'Insurance',
            'Telecommunication', 'Food & Allied', 'Cement',
            'Tannery Industries', 'Ceramics Sector', 'Paper & Printing',
            'Services & Real Estate', 'Travel & Leisure', 'Miscellaneous'
        ]
        for sec_name in dse_sectors:
            if not Sector.query.filter_by(name=sec_name).first():
                new_sector = Sector(name=sec_name)
                db.session.add(new_sector)

        # 4. Commit all the new records to the database
        db.session.commit()
        print("✅ Initial Sectors and Categories populated successfully.")


# --- ADD THESE TWO LINES ---
from app.routes import register_routes
register_routes(app)
# ---------------------------

if __name__ == '__main__':
    # Run the setup function when the script is executed directly
    setup_database()
    
    # We will uncomment the app.run() line later when we want to start the web server
    # app.run(debug=True)