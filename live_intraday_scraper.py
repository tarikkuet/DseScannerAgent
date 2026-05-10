# live_intraday_scraper.py
import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime, timedelta
from app import create_app
from app.models import db, Stock, IntradayTick

app = create_app()

def clean_num(val_str):
    val_str = str(val_str).replace(',', '').strip()
    if not val_str or val_str == '--' or val_str == '-':
        return 0.0
    try:
        return float(val_str)
    except ValueError:
        return 0.0

def fetch_live_ticks():
    """Scrapes the live DSE board and saves a snapshot to IntradayTick."""
    url = "https://www.dsebd.org/latest_share_price_scroll_l.php"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Connection': 'keep-alive'
    }

    print(f"\n📡 [{datetime.now().strftime('%H:%M:%S')}] Fetching live market data...")
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # The DSE live price table usually has a specific class
        table = soup.find('table', {'class': 'table table-bordered background-white shares-table fixedHeader'})
        
        if not table:
            print("   ❌ Could not find the data table on the page.")
            return

        rows = table.find_all('tr')
        if len(rows) < 2:
            print("   ❌ Table is empty.")
            return

        with app.app_context():
            # Get a quick dictionary of all stocks to avoid querying the DB 400 times
            all_stocks = {s.ticker: s.id for s in Stock.query.all()}
            saved_count = 0
            
            for row in rows[1:]: # Skip header
                cols = row.find_all('td')
                if len(cols) < 11:
                    continue
                
                ticker = cols[1].text.strip()
                
                # If we don't track this ticker in our DB, skip it
                if ticker not in all_stocks:
                    continue
                
                # Column 2 is LTP (Last Traded Price), Column 10 is Volume
                ltp = clean_num(cols[2].text)
                volume = int(clean_num(cols[10].text))
                
                # Only save a tick if trading has actually occurred (Volume > 0 and LTP > 0)
                if ltp > 0:
                    tick = IntradayTick(
                        stock_id=all_stocks[ticker],
                        current_price=ltp,
                        volume=volume
                    )
                    db.session.add(tick)
                    saved_count += 1
            
            db.session.commit()
            print(f"   ✅ Snapshot complete. Saved {saved_count} live ticks to database.")

    except requests.exceptions.Timeout:
        print("   ⏳ Network Timeout. DSE server is slow, will try again next cycle.")
    except Exception as e:
        print(f"   ❌ Error occurred: {e}")

def run_intraday_daemon(interval_minutes=30):
    """Runs the scraper continuously during DSE market hours."""
    print("🚀 Starting Intraday Daemon...")
    print(f"⚙️  Configured to poll every {interval_minutes} minutes during market hours.")
    
    while True:
        now = datetime.now()
        
        # Bangladesh Market Hours: Sunday (6) to Thursday (3)
        # Python weekday(): Monday=0, Tuesday=1, Wednesday=2, Thursday=3, Friday=4, Saturday=5, Sunday=6
        is_trading_day = now.weekday() in [0, 1, 2, 3, 6]
        
        # Market open 10:00 AM to 2:30 PM (14:30)
        is_trading_hours = (now.hour == 10 and now.minute >= 0) or \
                           (10 < now.hour < 14) or \
                           (now.hour == 14 and now.minute <= 30)

        if is_trading_day and is_trading_hours:
            fetch_live_ticks()
            print(f"   💤 Sleeping for {interval_minutes} minutes...\n")
            time.sleep(interval_minutes * 60)
        else:
            # If market is closed, sleep for 5 minutes and check again 
            # (prevents the script from shutting down entirely)
            print(f"   🛑 Market is currently closed ({now.strftime('%A %I:%M %p')}). Waiting...")
            time.sleep(300) 

if __name__ == '__main__':
    # You can change the interval to 15, 30, or 60 minutes
    run_intraday_daemon(interval_minutes=30)