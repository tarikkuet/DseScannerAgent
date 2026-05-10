# app/utils.py
import csv
import os
from datetime import datetime
from app.models import db, Stock, IntradayTick

def ingest_intraday_file(filepath):
    """Reads the AmiBroker CSV and bulk inserts it into the database."""
    if not os.path.exists(filepath):
        raise Exception(f"File not found: {filepath}")

    # Load all known stocks into a dictionary for fast lookups
    stock_dict = {s.ticker: s.id for s in Stock.query.all()}
    
    ticks_to_insert = []
    total_inserted = 0

    with open(filepath, mode='r', encoding='utf-8') as file:
        reader = csv.reader(file)
        
        for row in reader:
            if len(row) < 5:
                continue 
            
            ticker = row[0].strip()
            date_str = row[1].strip()
            time_str = row[2].strip()
            price_str = row[3].strip()
            volume_str = row[4].strip()

            if ticker.lower() == 'ticker' or 'date' in date_str.lower():
                continue

            if ticker not in stock_dict:
                continue

            try:
                timestamp = datetime.strptime(f"{date_str} {time_str}", "%Y%m%d %H%M%S")
                tick = IntradayTick(
                    stock_id=stock_dict[ticker],
                    timestamp=timestamp,
                    current_price=float(price_str),
                    volume=int(volume_str)
                )
                ticks_to_insert.append(tick)
                total_inserted += 1
                
                # BULK INSERT: Save to SQLite in chunks of 5,000
                if len(ticks_to_insert) >= 5000:
                    db.session.bulk_save_objects(ticks_to_insert)
                    db.session.commit()
                    ticks_to_insert = []
                    
            except ValueError as e:
                print(f"Warning: Skipping row due to error: {e}")

        # Commit any remaining rows
        if ticks_to_insert:
            db.session.bulk_save_objects(ticks_to_insert)
            db.session.commit()
            
    return total_inserted