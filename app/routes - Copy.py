# app/routes.py
from datetime import datetime, timedelta
from flask import render_template, request,redirect, url_for, jsonify
from app.models import db, Sector, Category, Stock, DailyPerformance, IntradayTick,WatchlistGroup
import os
import re
import shutil  # <-- Add this! It lets Python move files around
import pandas as pd
from collections import defaultdict
from sqlalchemy import func

def register_routes(app):
    @app.route('/')
    def index():
        return render_template('index.html')
        # 1. Get all 4 filter parameters from the URL
        selected_ticker_id = request.args.get('ticker')
        selected_cat = request.args.get('category')
        selected_sector = request.args.get('sector')
        selected_watchlist = request.args.get('watchlist')

        # 2. Base query
        query = Stock.query

        # 3. Apply filters dynamically
        if selected_ticker_id:
            query = query.filter(Stock.id == selected_ticker_id)
        if selected_cat:
            query = query.join(Category).filter(Category.name == selected_cat)
        if selected_sector:
            query = query.join(Sector).filter(Sector.name == selected_sector)
        if selected_watchlist:
            # Filter via the new Many-to-Many association table!
            query = query.join(Stock.watchlists).filter(WatchlistGroup.id == selected_watchlist)

        # Execute the query
        stocks = query.all()

        # 4. Get the latest prices
        latest_prices = {}
        for stock in stocks:
            latest_record = DailyPerformance.query.filter_by(stock_id=stock.id).order_by(DailyPerformance.trade_date.desc()).first()
            latest_prices[stock.id] = latest_record

        # 5. Data needed to populate the Filter Dropdowns
        all_stocks = Stock.query.order_by(Stock.ticker).all()
        sectors = Sector.query.all()
        categories = Category.query.all()
        watchlists = WatchlistGroup.query.all()

        return render_template(
            'index.html', 
            stocks=stocks,
            latest_prices=latest_prices,
            all_stocks=all_stocks,
            sectors=sectors,
            categories=categories,
            watchlists=watchlists,
            selected_ticker_id=selected_ticker_id,
            selected_cat=selected_cat,
            selected_sector=selected_sector,
            selected_watchlist=selected_watchlist
        )
    # --- NEW ROUTE: Manage Watchlists ---
    @app.route('/manage_watchlist', methods=['POST'])
    def manage_watchlist():
        # Get the form data
        action = request.form.get('action') # Will be 'save' or 'delete'
        watchlist_id = request.form.get('watchlist_id')
        name = request.form.get('name')
        description = request.form.get('description')
        
        # request.form.getlist() automatically grabs all selected items from a multi-select!
        stock_ids = request.form.getlist('stocks') 

        if action == 'delete' and watchlist_id:
            # Delete the entire watchlist (SQLAlchemy handles unlinking the stocks automatically)
            wl = WatchlistGroup.query.get(watchlist_id)
            if wl:
                db.session.delete(wl)
                db.session.commit()

        elif action == 'save' and name:
            if watchlist_id:
                # Update existing watchlist
                wl = WatchlistGroup.query.get(watchlist_id)
                wl.name = name
                wl.description = description
            else:
                # Create a brand new watchlist
                wl = WatchlistGroup(name=name, description=description)
                db.session.add(wl)

            # This is the magic of Many-to-Many! We just wipe the list and give it the new one.
            wl.stocks = [] 
            for sid in stock_ids:
                stock = Stock.query.get(sid)
                if stock:
                    wl.stocks.append(stock)
            
            db.session.commit()


    # --- NEW ROUTE: Master Data Management ---
    # --- ROUTE: Master Data Management ---
    @app.route('/data_management')
    def data_management():
        # 1. Get filter and pagination parameters from the URL
        sec_filter = request.args.get('sector', '')
        cat_filter = request.args.get('category', '')
        # Default to page 1, ensure it's an integer
        page = request.args.get('page', 1, type=int) 

        # 2. Build the base query for Stocks
        stock_query = Stock.query

        # 3. Apply Filters if the user selected them
        if sec_filter:
            stock_query = stock_query.join(Sector).filter(Sector.name == sec_filter)
        if cat_filter:
            stock_query = stock_query.join(Category).filter(Category.name == cat_filter)

        # 4. Paginate! Get 50 items per page. 
        # error_out=False prevents crashing if a user types page=999 in the URL
        paginated_stocks = stock_query.order_by(Stock.ticker).paginate(page=page, per_page=50, error_out=False)

        # 5. Fetch all Sectors and Categories for the dropdowns and the other tabs
        sectors = Sector.query.order_by(Sector.name).all()
        categories = Category.query.order_by(Category.name).all()
        
        return render_template(
            'data_management.html',
            stocks=paginated_stocks, # We are now passing the Pagination Object, not just a list!
            sectors=sectors,
            categories=categories,
            sec_filter=sec_filter,
            cat_filter=cat_filter
        )
    # --- ROUTE: Data Health UI Page ---
    @app.route('/data_health')
    def data_health():
        return render_template('data_health.html')

    # --- API: Check for missing dates ---
    @app.route('/api/check_gaps', methods=['GET'])
    def api_check_gaps():
        # Get start/end dates from the URL, or default to a 3-month window
        end_date_str = request.args.get('end_date', datetime.today().strftime('%Y-%m-%d'))
        start_date_str = request.args.get('start_date', (datetime.today() - timedelta(days=90)).strftime('%Y-%m-%d'))
        
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

        # Ask SQLite for all unique dates it currently holds
        existing_dates_query = db.session.query(DailyPerformance.trade_date).filter(
            DailyPerformance.trade_date >= start_date,
            DailyPerformance.trade_date <= end_date
        ).distinct().all()
        
        saved_dates = {row[0] for row in existing_dates_query}
        missing_dates = []
        
        current = end_date
        while current >= start_date:
            # Skip Friday (4) and Saturday (5)
            if current.weekday() not in [4, 5]: 
                if current not in saved_dates:
                    missing_dates.append(current.strftime('%Y-%m-%d'))
            current -= timedelta(days=1)
            
        return jsonify({
            'start_date': start_date_str,
            'end_date': end_date_str,
            'total_missing': len(missing_dates),
            'missing_dates': missing_dates # This is a list of strings: ['2026-04-15', '2026-04-12']
        })

    # --- API: Trigger a single day sync ---
    @app.route('/api/sync_day', methods=['POST'])
    def api_sync_day():
        data = request.get_json()
        target_date = data.get('date')
        
        if not target_date:
            return jsonify({'success': False, 'message': 'No date provided'}), 400
            
        print(f"UI requested surgical sync for: {target_date}")
        
        # LAZY IMPORT: We import it right here to break the circle!
        from seed_dse_archive import scrape_dse_archive_for_date

        # Call our scraper function!
        status = scrape_dse_archive_for_date(target_date)
        
        if status == "SUCCESS":
            return jsonify({'success': True, 'status': 'success', 'message': f'Data loaded for {target_date}'})
        elif status == "CLOSED":
            return jsonify({'success': True, 'status': 'closed', 'message': f'Market was closed on {target_date} (Holiday)'})
        else:
            return jsonify({'success': False, 'status': 'error', 'message': f'Network error fetching {target_date}'}), 500


    # --- ROUTE: Main Dashboard ---
    @app.route('/dashboard')
    def dashboard():
        # Fetch all stocks to populate the dropdown menu
        stocks = Stock.query.order_by(Stock.ticker).all()
        return render_template('dashboard.html', stocks=stocks)

    # --- API: Unified Multi-Timeframe Chart Data ---
    @app.route('/api/chart_data/<ticker>', methods=['GET'])
    def api_chart_data(ticker):
        # Default to Daily ('D') if no timeframe is provided
        timeframe = request.args.get('tf', 'D') 
        
        stock = Stock.query.filter_by(ticker=ticker).first()
        if not stock:
            return jsonify({'candlestick': [], 'volume': [], 'ticker': ticker, 'name': 'Unknown'})

        chart_data = []
        volume_data = []

        # ==========================================
        # SCENARIO A: DAILY TIMEFRAME (Master Data)
        # ==========================================
        if timeframe == 'D':
            history = DailyPerformance.query.filter_by(stock_id=stock.id).order_by(DailyPerformance.trade_date.asc()).all()
            for row in history:
                date_str = row.trade_date if isinstance(row.trade_date, str) else row.trade_date.strftime('%Y-%m-%d')
                
                chart_data.append({
                    'time': date_str,
                    'open': row.open_price,
                    'high': row.high_price,
                    'low': row.low_price,
                    'close': row.close_price
                })
                
                color = 'rgba(38, 166, 154, 0.5)' if row.close_price >= row.open_price else 'rgba(239, 83, 80, 0.5)'
                volume_data.append({'time': date_str, 'value': row.volume, 'color': color})

        # ==========================================
        # SCENARIO B: INTRADAY TIMEFRAME (Pandas Resampling)
        # ==========================================
        else:
            # 1. Fetch all raw ticks from the database
            ticks = IntradayTick.query.filter_by(stock_id=stock.id).order_by(IntradayTick.timestamp.asc()).all()
            if not ticks:
                return jsonify({'candlestick': [], 'volume': [], 'ticker': stock.ticker, 'name': stock.ticker})

            # 2. Load into a Pandas DataFrame
            data = [{'timestamp': t.timestamp, 'price': t.current_price, 'volume': t.volume} for t in ticks]
            df = pd.DataFrame(data)
            df.set_index('timestamp', inplace=True)

            # 3. The Magic Engine: Resample the ticks into the requested timeframe (e.g., '15min', '1h')
            resampled = df.resample(timeframe).agg({
                'price': ['first', 'max', 'min', 'last'], # Open, High, Low, Close
                'volume': 'sum'                           # Total Volume for the period
            }).dropna() # Drop any empty time buckets

            # Flatten the multi-level columns Pandas creates
            resampled.columns = ['open', 'high', 'low', 'close', 'volume']

            # 4. Format for TradingView (Intraday requires UNIX timestamps)
            for timestamp, row in resampled.iterrows():
                time_val = int(timestamp.timestamp())
                
                chart_data.append({
                    'time': time_val,
                    'open': row['open'],
                    'high': row['high'],
                    'low': row['low'],
                    'close': row['close']
                })
                
                color = 'rgba(38, 166, 154, 0.5)' if row['close'] >= row['open'] else 'rgba(239, 83, 80, 0.5)'
                volume_data.append({'time': time_val, 'value': int(row['volume']), 'color': color})

        return jsonify({
            'candlestick': chart_data, 
            'volume': volume_data, 
            'ticker': stock.ticker,
            'name': stock.ticker
        })

    # --- ROUTE: Intraday Ingestion UI ---
    @app.route('/intraday_imports')
    def intraday_imports():
        return render_template('intraday_imports.html')

    # --- API: Scan Drop Zone for CSVs ---
    @app.route('/api/scan_intraday')
    def api_scan_intraday():
        # Point to the imports/intraday folder
        drop_zone = os.path.join(os.getcwd(), 'imports', 'intraday')
        
        if not os.path.exists(drop_zone):
            os.makedirs(drop_zone)
            
        pending_files = []
        for filename in os.listdir(drop_zone):
            if filename.endswith('.csv'):
                # Extract the date from AmiBroker_Intraday_YYYY-MM-DD.csv using Regex
                match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
                date_str = match.group(1) if match else "Unknown Date"
                
                # Check file size to display in the UI
                filepath = os.path.join(drop_zone, filename)
                size_kb = os.path.getsize(filepath) // 1024
                
                pending_files.append({
                    'filename': filename,
                    'date': date_str,
                    'size_kb': size_kb
                })
                
        # Sort files by date, newest first
        pending_files.sort(key=lambda x: x['date'], reverse=True)
        return jsonify({'status': 'success', 'files': pending_files})

    # --- API: Process a Specific File ---
    @app.route('/api/process_intraday', methods=['POST'])
    def api_process_intraday():
        data = request.get_json()
        filename = data.get('filename')
        
        if not filename:
            return jsonify({'success': False, 'message': 'No filename provided.'}), 400
            
        imports_dir = os.path.join(os.getcwd(), 'imports', 'intraday')
        archive_dir = os.path.join(os.getcwd(), 'imports', 'archive')
        filepath = os.path.join(imports_dir, filename)
        
        # NEW IMPORT: Pulling from our shiny new utils file
        from app.utils import ingest_intraday_file
        
        try:
           # 1. Run the bulk ingestion
            total_rows = ingest_intraday_file(filepath)
            
            # 2. Make sure the archive folder exists
            if not os.path.exists(archive_dir):
                os.makedirs(archive_dir)
                
            # 3. Move the file out of the drop zone
            archive_path = os.path.join(archive_dir, filename)
            shutil.move(filepath, archive_path)
            
            return jsonify({'success': True, 'message': f'Successfully injected {total_rows} rows from {filename}'})
                        
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    # --- API: Fetch Intraday Line Data ---
    @app.route('/api/intraday_data/<ticker>', methods=['GET'])
    def api_intraday_data(ticker):
        stock = Stock.query.filter_by(ticker=ticker).first()
        if not stock:
            return jsonify([])

        # 1. Find the absolute latest tick so we know what "today" is
        latest_tick = IntradayTick.query.filter_by(stock_id=stock.id)\
            .order_by(IntradayTick.timestamp.desc()).first()
            
        if not latest_tick:
            return jsonify([])

        # 2. Define the start and end of that specific day
        latest_date = latest_tick.timestamp.date()
        start_of_day = datetime.combine(latest_date, datetime.min.time())
        end_of_day = datetime.combine(latest_date, datetime.max.time())

        # 3. Fetch all ticks for that specific day
        ticks = IntradayTick.query.filter(
            IntradayTick.stock_id == stock.id,
            IntradayTick.timestamp >= start_of_day,
            IntradayTick.timestamp <= end_of_day
        ).order_by(IntradayTick.timestamp.asc()).all()

        intraday_data = []
        for t in ticks:
            # TradingView requires intraday time as a UNIX timestamp in seconds
            intraday_data.append({
                'time': int(t.timestamp.timestamp()),
                'value': t.current_price
            })

        return jsonify(intraday_data)
    from app.models import Sector, Category

    # --- ROUTE: Market Screener UI ---
    @app.route('/screener')
    def screener():
        # Fetch sectors and categories to populate the filter dropdowns
        sectors = Sector.query.order_by(Sector.name).all()
        categories = Category.query.order_by(Category.name).all()
        return render_template('screener.html', sectors=sectors, categories=categories)

    # --- API: Fetch All Stocks for Screener ---
    # --- API: Fetch All Stocks for Screener (OPTIMIZED) ---
    @app.route('/api/screener_data')
    def api_screener_data():
        stocks = Stock.query.all()
        
        # 1. Find the exact last 11 trading dates for the whole market (1 Query)
        # 1. Find the exact last 11 trading dates for the whole market (1 Query)
        recent_dates_query = DailyPerformance.query.with_entities(DailyPerformance.trade_date)\
            .distinct()\
            .order_by(DailyPerformance.trade_date.desc())\
            .limit(11).all()
            
        recent_dates = [d[0] for d in recent_dates_query]

        if not recent_dates:
            return jsonify([])

        # 2. Fetch ALL performance data for those specific dates in bulk (1 Query)
        bulk_performance = DailyPerformance.query\
            .filter(DailyPerformance.trade_date.in_(recent_dates))\
            .order_by(DailyPerformance.stock_id, DailyPerformance.trade_date.desc()).all()

        # 3. Group the data by stock_id in RAM (Lightning fast)
        perf_by_stock = defaultdict(list)
        for p in bulk_performance:
            perf_by_stock[p.stock_id].append(p)

        screener_data = []

        # 4. Do the math using our memory dictionary instead of hitting the DB
        for stock in stocks:
            recent_data = perf_by_stock.get(stock.id, [])
            
            if not recent_data:
                continue
                
            latest = recent_data[0]
            
            # Calculate Price Change (Latest Day)
            change = 0
            pct_change = 0
            if latest.ycp and latest.ycp > 0:
                change = latest.close_price - latest.ycp
                pct_change = (change / latest.ycp) * 100

            # NEW: Calculate 5-Day % Change (Excluding Latest Day)
            pct_change_5d = 0
            if len(recent_data) > 6:
                end_price = recent_data[1].close_price     # Yesterday's Close
                start_price = recent_data[6].close_price   # Close 6 days ago (Baseline)
                if start_price > 0:
                    pct_change_5d = ((end_price - start_price) / start_price) * 100

            # Calculate 10-Day Average Volume and Volume % Change
            avg_vol_10d = 0
            vol_pct_change = 0
            
            if len(recent_data) > 1:
                previous_days = recent_data[1:] 
                total_vol = sum(day.volume for day in previous_days)
                avg_vol_10d = total_vol / len(previous_days)
                
                if avg_vol_10d > 0:
                    vol_pct_change = ((latest.volume - avg_vol_10d) / avg_vol_10d) * 100

            screener_data.append({
                'ticker': stock.ticker,
                'sector': stock.sector.name if stock.sector else 'Uncategorized',
                'category': stock.category.name if stock.category else '-',
                'price': round(latest.close_price, 2),
                'change': round(change, 2),
                'pct_change': round(pct_change, 2),
                'pct_change_5d': round(pct_change_5d, 2), # NEW DATAPOINT
                'volume': latest.volume,
                'avg_vol_10d': int(avg_vol_10d),
                'vol_pct_change': round(vol_pct_change, 2)
            })

        return jsonify(screener_data)
    
        # Redirect back to the dashboard immediately
        return redirect(request.referrer or url_for('index'))