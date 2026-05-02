# seed_watchlist.py
from app import create_app
from app.models import db, Stock, WatchlistItem

app = create_app()

def seed_watchlist():
    with app.app_context():
        # Let's tag three specific stocks we seeded earlier
        tags = [
            {'ticker': 'SINOBANGLA', 'setup': 'Order Block', 'notes': 'Bullish OB tested on daily chart.'},
            {'ticker': 'BRACBANK', 'setup': 'Liquidity Sweep', 'notes': 'Swept previous week low, expecting reversal.'},
            {'ticker': 'GP', 'setup': 'CHoCH', 'notes': 'Change of Character detected with high volume.'}
        ]

        for tag in tags:
            stock = Stock.query.filter_by(ticker=tag['ticker']).first()
            if stock:
                # Check if it's already in the watchlist
                exists = WatchlistItem.query.filter_by(stock_id=stock.id).first()
                if not exists:
                    new_item = WatchlistItem(
                        stock_id=stock.id,
                        setup_type=tag['setup'],
                        notes=tag['notes']
                    )
                    db.session.add(new_item)
                    print(f"✅ Tagged {stock.ticker} with {tag['setup']}")
        
        db.session.commit()
        print("Watchlist seeding complete!")

if __name__ == '__main__':
    seed_watchlist()