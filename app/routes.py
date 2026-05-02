# app/routes.py
from datetime import datetime, timedelta
from flask import render_template, request,redirect, url_for, jsonify
from app.models import db, Sector, Category, Stock, DailyPerformance, WatchlistGroup



def register_routes(app):
    @app.route('/')
    def index():
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
        
        
        # Redirect back to the dashboard immediately
        return redirect(request.referrer or url_for('index'))