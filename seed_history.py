# seed_history.py
import yfinance as yf
import time
from app import create_app
from app.models import db, Stock, DailyPerformance

app = create_app()

def fetch_benchmark_history():
    with app.app_context():
        stocks = Stock.query.all()
        total = len(stocks)
        
        print(f"⏱️ Starting Benchmark: Fetching 5 days of data for {total} stocks...")
        
        # Start the timer!
        start_time = time.time()
        
        success_count = 0
        missing_count = 0

        for i, stock in enumerate(stocks, 1):
            yf_ticker = f"{stock.ticker}.BD"
            
            try:
                # CHANGED: Just pull the last 5 days (roughly 2-3 trading days depending on weekends)
                ticker_data = yf.Ticker(yf_ticker)
                hist = ticker_data.history(period="5d")
                
                if hist.empty:
                    missing_count += 1
                    print(f"[{i}/{total}] ⚠️ No data for {stock.ticker}        ", end='\r')
                    continue
                
                prev_close = None 

                for index, row in hist.iterrows():
                    trade_date = index.date()
                    existing = DailyPerformance.query.filter_by(stock_id=stock.id, trade_date=trade_date).first()
                    
                    if not existing:
                        daily_perf = DailyPerformance(
                            stock_id=stock.id,
                            trade_date=trade_date,
                            open_price=row['Open'],
                            high_price=row['High'],
                            low_price=row['Low'],
                            close_price=row['Close'],
                            ycp=prev_close,       
                            volume=int(row['Volume'])
                        )
                        db.session.add(daily_perf)
                    
                    prev_close = row['Close']
                
                db.session.commit()
                success_count += 1
                print(f"[{i}/{total}] ✅ Saved benchmark for {stock.ticker}                 ", end='\r')
                
            except Exception as e:
                missing_count += 1
                db.session.rollback()
                print(f"[{i}/{total}] ❌ Error on {stock.ticker}: {e}                     ", end='\r')

        # Stop the timer!
        end_time = time.time()
        elapsed_seconds = end_time - start_time

        print(f"\n\n🏁 Benchmark Complete!")
        print(f"✅ Successfully pulled data for {success_count} stocks.")
        print(f"⏱️ Total Time Elapsed: {elapsed_seconds:.2f} seconds ({elapsed_seconds/60:.2f} minutes)")

if __name__ == '__main__':
    fetch_benchmark_history()