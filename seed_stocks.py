# seed_stocks.py
from app import create_app
from app.models import db, Stock, Sector, Category

# Create the app using our factory
app = create_app()

def get_or_create_sector(name):
    sector = Sector.query.filter_by(name=name).first()
    if not sector:
        sector = Sector(name=name)
        db.session.add(sector)
        db.session.commit() # Save it immediately so we have an ID
    return sector

def get_or_create_category(name):
    category = Category.query.filter_by(name=name).first()
    if not category:
        category = Category(name=name)
        db.session.add(category)
        db.session.commit() # Save it immediately so we have an ID
    return category

def seed_initial_stocks():
    with app.app_context():
        stocks_data = [
            {'ticker': 'SINOBANGLA', 'name': 'Sinobangla Industries Ltd.', 'sector': 'Engineering', 'category': 'A'},
            {'ticker': 'SQURPHARMA', 'name': 'Square Pharmaceuticals PLC', 'sector': 'Pharmaceuticals & Chemicals', 'category': 'A'},
            {'ticker': 'GP', 'name': 'Grameenphone Ltd.', 'sector': 'Telecommunication', 'category': 'A'},
            {'ticker': 'BRACBANK', 'name': 'BRAC Bank PLC', 'sector': 'Bank', 'category': 'A'},
            {'ticker': 'BATBC', 'name': 'British American Tobacco bd co', 'sector': 'Food & Allied', 'category': 'A'},
            {'ticker': 'WALTONHIL', 'name': 'Walton Hi-Tech Industries PLC', 'sector': 'Engineering', 'category': 'A'}
        ]

        print("🌱 Starting stock seeding process...")

        added_count = 0
        for data in stocks_data:
            if not Stock.query.filter_by(ticker=data['ticker']).first():
                # Dynamically fetch or create the Sector and Category
                sector = get_or_create_sector(data['sector'])
                category = get_or_create_category(data['category'])

                new_stock = Stock(
                    ticker=data['ticker'],
                    company_name=data['name'],
                    sector_id=sector.id,
                    category_id=category.id
                )
                db.session.add(new_stock)
                print(f"  -> Added {data['ticker']} to database.")
                added_count += 1
            else:
                print(f"  ⏩ Skipped {data['ticker']}: Already exists in database.")
        
        db.session.commit()
        print(f"✅ Seeding complete! {added_count} new stocks added.")

if __name__ == '__main__':
    seed_initial_stocks()