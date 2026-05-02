# smart_sync.py
import time
from datetime import timedelta
from app import create_app
from app.models import db, DailyPerformance
from seed_dse_archive import scrape_dse_archive_for_date

app = create_app()

def find_and_fill_gaps():
    with app.app_context():
        print("🔍 Analyzing database for missing dates...")
        
        # 1. Ask SQLite for every unique date it currently holds
        existing_dates_query = db.session.query(DailyPerformance.trade_date).distinct().all()
        
        # Unpack the results into a fast Python Set
        saved_dates = {row[0] for row in existing_dates_query}

        if not saved_dates:
            print("❌ Database is empty. Please run the Time Machine script first.")
            return

        # 2. Find our boundaries
        max_date = max(saved_dates)
        min_date = min(saved_dates)
        
        print(f"📊 Timeline: {min_date} to {max_date}")
        print(f"✅ Total trading days currently saved: {len(saved_dates)}")

        # 3. Walk the calendar to find the gaps
        missing_dates = []
        current = max_date
        
        while current >= min_date:
            # If it's Sunday (6) through Thursday (3), check if we have it
            if current.weekday() not in [4, 5]: 
                if current not in saved_dates:
                    # Convert to string format for the scraper
                    missing_dates.append(current.strftime('%Y-%m-%d'))
            
            # Move back one day
            current -= timedelta(days=1)

        if not missing_dates:
            print("\n🎉 No gaps found! Your historical data is perfectly continuous.")
            return

        print(f"\n🎯 Identified {len(missing_dates)} missing weekdays. Commencing surgical strike...\n")

        # 4. Scrape ONLY the missing dates
        still_missing = []
        for i, date_str in enumerate(missing_dates, 1):
            print(f"📅 Fetching missing date: {date_str} [{i}/{len(missing_dates)}]")
            
            # Re-use our existing scraper function!
            status = scrape_dse_archive_for_date(date_str)
            
            if status == "ERROR":
                still_missing.append(date_str)
                
            # Be polite to the DSE servers
            time.sleep(2)

        # 5. Final Report
        if still_missing:
            print(f"\n\n⚠️ Finished, but {len(still_missing)} dates still failed due to network errors.")
            print(f"Failed dates: {', '.join(still_missing)}")
        else:
            print("\n\n🏆 All historical gaps successfully filled!")

if __name__ == '__main__':
    find_and_fill_gaps()