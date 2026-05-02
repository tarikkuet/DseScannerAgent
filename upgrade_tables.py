# upgrade_tables.py
from app import create_app
from app.models import db, DailyPerformance, IntradayTick

app = create_app()

def upgrade_specific_tables():
    with app.app_context():
        print("⚙️ Dropping old performance tables...")
        # Drop ONLY the specific tables (checkfirst=True prevents errors if they don't exist yet)
        DailyPerformance.__table__.drop(db.engine, checkfirst=True)
        IntradayTick.__table__.drop(db.engine, checkfirst=True)
        
        print("🔨 Recreating tables with new schema (ycp column)...")
        # Recreate ONLY those specific tables
        DailyPerformance.__table__.create(db.engine)
        IntradayTick.__table__.create(db.engine)
        
        print("✅ Success! The new schema is ready, and your Master Data is safe.")

if __name__ == '__main__':
    upgrade_specific_tables()