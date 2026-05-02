# app/routes.py
from flask import render_template, request,redirect, url_for
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

        # Redirect back to the dashboard immediately
        return redirect(request.referrer or url_for('index'))