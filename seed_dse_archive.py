# seed_dse_archive.py
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
from app import create_app
from app.models import db, Stock, DailyPerformance

app = create_app()

def clean_num(val_str):
    val_str = val_str.replace(',', '').strip()
    if not val_str or val_str == '--' or val_str == '-':
        return 0.0
    try:
        return float(val_str)
    except ValueError:
        return 0.0

def scrape_dse_archive_for_date(target_date_str):
    """Scrapes a single date and returns True if data was found, False if closed."""
    """Returns 'SUCCESS', 'CLOSED', or 'ERROR'"""
    url = f"https://www.dsebd.org/day_end_archive.php?startDate={target_date_str}&endDate={target_date_str}&inst=All%20Instrument&archive=data"
    # UPGRADED HEADERS: Makes the script look exactly like a real Chrome browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=45)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        tables = soup.find_all('table')
        data_table = max(tables, key=lambda t: len(t.find_all('tr'))) if tables else None
                
        if not data_table or len(data_table.find_all('tr')) < 5:
            print(f"   ⏩ No data (Market likely closed/Holiday)")
            return False
            
        rows = data_table.find_all('tr')
        target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
        
        with app.app_context():
            success_count = 0
            for row in rows[1:]:
                cols = row.find_all('td')
                if len(cols) < 12: 
                    continue
                    
                ticker = cols[2].text.strip()
                stock = Stock.query.filter_by(ticker=ticker).first()
                if not stock:
                    continue
                    
                try:
                    open_price = clean_num(cols[6].text)
                    high_price = clean_num(cols[4].text)
                    low_price = clean_num(cols[5].text)
                    close_price = clean_num(cols[7].text)
                    ycp = clean_num(cols[8].text)
                    volume = int(clean_num(cols[11].text))
                    
                    existing = DailyPerformance.query.filter_by(stock_id=stock.id, trade_date=target_date).first()
                    
                    if not existing:
                        daily_perf = DailyPerformance(
                            stock_id=stock.id,
                            trade_date=target_date,
                            open_price=open_price,
                            high_price=high_price,
                            low_price=low_price,
                            close_price=close_price,
                            ycp=ycp,
                            volume=volume
                        )
                        db.session.add(daily_perf)
                        success_count += 1
                except Exception:
                    pass
                    
            db.session.commit()
            print(f"   ✅ Saved {success_count} records.")
            return True

    except Exception as e:
        print(f"   ❌ Network Error: {e}")
        return False

def run_historical_seeder():
    # Start date: Thursday, April 30, 2026
    current_date = datetime(2026, 4, 30)
    
    # Target: 65 successful trading days (roughly 3 months)
    target_trading_days = 65
    successful_days = 0
    
    print(f"🚀 Starting 3-Month Time Machine (Targeting {target_trading_days} trading days).")
    start_time = time.time()
    
    while successful_days < target_trading_days:
        # Python weekday(): Monday is 0, Sunday is 6. 
        # Bangladesh weekend is Friday (4) and Saturday (5)
        if current_date.weekday() not in [4, 5]:
            date_str = current_date.strftime('%Y-%m-%d')
            print(f"\n📅 Fetching: {date_str} [{successful_days + 1}/{target_trading_days}]")
            
            was_open = scrape_dse_archive_for_date(date_str)
            
            if was_open:
                successful_days += 1
                
            # BE POLITE TO DSE SERVERS: 2-second pause between requests
            time.sleep(2) 
        else:
            # It's a weekend, silently skip
            pass
            
        # Move back one day in time
        current_date -= timedelta(days=1)

    end_time = time.time()
    minutes = (end_time - start_time) / 60
    print(f"\n\n🏁 TIME MACHINE COMPLETE!")
    print(f"✅ Successfully downloaded {successful_days} days of market data.")
    print(f"⏱️ Total execution time: {minutes:.2f} minutes.")

if __name__ == '__main__':
    run_historical_seeder()