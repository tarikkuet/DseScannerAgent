# update_master_data.py
import requests
from bs4 import BeautifulSoup
import time
from app import create_app
from app.models import db, Stock, Sector, Category

app = create_app()

def get_or_create_sector(name):
    # Clean up any weird characters or spaces from the website
    clean_name = name.strip()
    if not clean_name: 
        clean_name = "General / Unassigned"
        
    sector = Sector.query.filter_by(name=clean_name).first()
    if not sector:
        sector = Sector(name=clean_name)
        db.session.add(sector)
        db.session.commit()
    return sector

def get_or_create_category(name):
    clean_name = name.strip()
    if not clean_name:
        clean_name = "N"
        
    category = Category.query.filter_by(name=clean_name).first()
    if not category:
        category = Category(name=clean_name)
        db.session.add(category)
        db.session.commit()
    return category

def run_deep_scraper():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    with app.app_context():
        # Get all the stocks we saved from the first script
        stocks = Stock.query.all()
        total_stocks = len(stocks)

        print(f"🚀 Starting Deep Scrape for {total_stocks} companies. This will take about 3-4 minutes...")

        updated_count = 0

        for i, stock in enumerate(stocks, 1):
            url = f"https://www.dsebd.org/displayCompany.php?name={stock.ticker}"

            try:
                response = requests.get(url, headers=headers, timeout=15)
                soup = BeautifulSoup(response.text, 'html.parser')

                # Defaults just in case the page is broken
                sector_name = "General / Unassigned"
                category_name = "N"

                # DSE puts this data in a table. We look through all cells to find the labels.
                tds = soup.find_all(['td', 'th'])
                for index, elem in enumerate(tds):
                    # Clean the text and remove colons just in case
                    text = elem.text.strip().replace(':', '').strip()
                    
                    if text == "Sector" and index + 1 < len(tds):
                        sector_name = tds[index + 1].text.strip()
                    
                    elif text == "Market Category" and index + 1 < len(tds):
                        category_name = tds[index + 1].text.strip()

                # 1. Ensure the Sector and Category exist in the database
                sector = get_or_create_sector(sector_name)
                category = get_or_create_category(category_name)

                # 2. Update our stock with the correct IDs
                stock.sector_id = sector.id
                stock.category_id = category.id

                # Save to database
                db.session.commit()
                updated_count += 1

                # Print progress on the same line
                print(f"[{i}/{total_stocks}] Mapped {stock.ticker} -> {sector_name} | Cat: {category_name}       ", end='\r')

                # BE POLITE TO THE SERVER: Pause for 0.5 seconds
                time.sleep(0.5)

            except Exception as e:
                print(f"\n❌ Error fetching {stock.ticker}: {e}")

        print(f"\n\n🎉 Master Data Update Complete! {updated_count} companies fully mapped.")

        # Cleanup: Delete any Sectors/Categories that are now completely empty
        empty_sectors = Sector.query.filter(~Sector.stocks.any()).all()
        for s in empty_sectors: db.session.delete(s)
        
        empty_cats = Category.query.filter(~Category.stocks.any()).all()
        for c in empty_cats: db.session.delete(c)
        db.session.commit()

if __name__ == '__main__':
    run_deep_scraper()