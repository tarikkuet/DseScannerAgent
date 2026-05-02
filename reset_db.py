# reset_db.py
from app import create_app
from app.models import db

# 1. Initialize the app
app = create_app()

# 2. Rebuild the database tables
with app.app_context():
    # DROP ALL TABLES FIRST (This wipes the data!)
    db.drop_all()

    # Recreate the blank tables
    db.create_all()
    print("✅ Database successfully rebuilt with the new Watchlist architecture!")