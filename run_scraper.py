# run_scraper.py
import random
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from app import create_app
from app.models import db, Stock, DailyPerformance

# Initialize the Flask app context so we can talk to the database
app = create_app()

def run_daily_scraper():
    with app.app_context():
        # 1. Get all the stocks we seeded earlier
        stocks = Stock.query.all()
        print(f"🔍 Found {len(stocks)} stocks in the database. Starting scanner engine...")
        
        # Use today's date for the record
        today = datetime.now().date()

        # Headers to mimic a real web browser (prevents basic blocking)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        for stock in stocks:
            print(f"Fetching market data for {stock.ticker}...")
            
            try:
                # The actual DSE URL format
                url = f"https://www.dsebd.org/displayCompany.php?name={stock.ticker}"
                
                # --- THE FETCH & PARSE PHASE ---
                # response = requests.get(url, headers=headers)
                # soup = BeautifulSoup(response.text, 'html.parser')
                # (We will write the complex HTML table extraction logic here later)
                
                # For our initial pipeline test, we generate realistic DSE price data
                base_price = random.uniform(50, 300)
                open_price = round(base_price, 2)
                close_price = round(base_price + random.uniform(-5, 5), 2)
                high_price = round(max(open_price, close_price) + random.uniform(0, 3), 2)
                low_price = round(min(open_price, close_price) - random.uniform(0, 3), 2)
                volume = random.randint(10000, 500000)

                # --- THE DATABASE PHASE ---
                
                # 2. Check if we already scraped this stock today! 
                # This tests the unique constraint (_perf_stock_date_uc) we built in models.py
                existing_record = DailyPerformance.query.filter_by(
                    stock_id=stock.id, 
                    trade_date=today
                ).first()

                if existing_record:
                    print(f"  ⏩ Skipped {stock.ticker}: Data already exists for today.")
                    continue

                # 3. Create the new performance record
                new_perf = DailyPerformance(
                    stock_id=stock.id,
                    trade_date=today,
                    open_price=open_price,
                    high_price=high_price,
                    low_price=low_price,
                    close_price=close_price,
                    volume=volume
                )
                
                db.session.add(new_perf)
                print(f"  ✅ Saved OHLCV for {stock.ticker}: Close={close_price}, Vol={volume}")
                
            except Exception as e:
                print(f"  ❌ Error processing {stock.ticker}: {e}")

        # 4. Commit the transaction to save all records permanently
        db.session.commit()
        print("🎉 Daily performance update complete!")

if __name__ == '__main__':
    run_daily_scraper()