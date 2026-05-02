# dse_initializer.py
import requests
from bs4 import BeautifulSoup
from app import create_app
from app.models import db, Stock, Sector, Category

app = create_app()

def get_or_create_sector(name):
    # Clean up whitespace just in case the website is messy
    clean_name = name.strip() 
    sector = Sector.query.filter_by(name=clean_name).first()
    if not sector:
        sector = Sector(name=clean_name)
        db.session.add(sector)
        db.session.commit()
    return sector

def get_or_create_category(name):
    clean_name = name.strip()
    category = Category.query.filter_by(name=clean_name).first()
    if not category:
        category = Category(name=clean_name)
        db.session.add(category)
        db.session.commit()
    return category

def scrape_dse_companies():
    """Scrapes the DSE website to build the master list of stocks."""
    
    # We use a header to pretend we are a real web browser (Chrome), 
    # otherwise some servers block automated Python scripts.
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    # The URL where DSE lists latest share prices and categories
    url = "https://www.dsebd.org/latest_share_price_scroll_l.php"
    
    print(f"🌐 Connecting to {url}...")
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status() # Check if the download was successful
    except Exception as e:
        print(f"❌ Failed to connect to DSE website: {e}")
        return

    print("✅ Connected! Parsing market data...")
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find the main data table on the page (DSE uses a specific class for their tables)
    table = soup.find('table', {'class': 'table table-bordered background-white shares-table fixedHeader'})
    
    if not table:
         print("❌ Could not find the data table. The DSE website structure may have changed.")
         return

    # Skip the first row (the header) and loop through the rest
    rows = table.find_all('tr')[1:] 
    
    added_count = 0
    with app.app_context():
        for row in rows:
            cols = row.find_all('td')
            # Make sure it's a valid row with enough columns
            if len(cols) >= 4: 
                # Extract the text and remove extra spaces
                ticker = cols[1].text.strip()
                # Some rows have weird characters or are empty, skip them
                if not ticker or ticker == 'Ticker': 
                    continue
                    
                # FIX: Hardcode these for now instead of grabbing the LTP column
                category_name = 'N' 
                sector_name = 'General / Unassigned'

                # Check if stock already exists
                existing_stock = Stock.query.filter_by(ticker=ticker).first()
                if not existing_stock:
                    sector = get_or_create_sector(sector_name)
                    category = get_or_create_category(category_name)
                    
                    new_stock = Stock(
                        ticker=ticker,
                        company_name=ticker, # Using ticker as placeholder for company name
                        sector_id=sector.id,
                        category_id=category.id
                    )
                    db.session.add(new_stock)
                    added_count += 1
                    # Print on the same line to save screen space
                    print(f"  -> Added: {ticker} (Cat: {category_name})", end='\r') 
        
        db.session.commit()
        print(f"\n🎉 Initialization complete! {added_count} new stocks saved to the database.")

if __name__ == '__main__':
    scrape_dse_companies()