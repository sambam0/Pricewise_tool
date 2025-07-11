# Flask application for a multi-module cost and pricing analysis tool
# This application consists of four modules:
# 1. Cost Calculator: Calculates the fully loaded cost of a product.
# 2. Market Analyzer: Analyzes the competitive landscape.
# 3. Pricing Strategy Modeler: Generates pricing strategies based on costs and market data. 
# 4. Optimization Simulator: Allows "What-If" analysis for cost and price changes.


from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# Helper function to safely convert form inputs to float
def to_float(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0

@app.route('/', methods=['GET', 'POST'])
def module1_cost_calculator():
    """Module 1: Calculate the fully loaded cost of a product."""
    if request.method == 'POST':
        # --- Collect form data ---
        # Direct Costs
        cost_materials = to_float(request.form.get('cost_materials'))
        labor_hours = to_float(request.form.get('labor_hours'))
        labor_rate = to_float(request.form.get('labor_rate'))
        packaging_cost = to_float(request.form.get('packaging_cost'))
        shipping_cost = to_float(request.form.get('shipping_cost'))

        # Indirect Costs
        monthly_overhead = to_float(request.form.get('monthly_overhead'))
        monthly_production_volume = to_float(request.form.get('monthly_production_volume'))
        if monthly_production_volume == 0:
            monthly_production_volume = 1 # Avoid division by zero

        # --- Perform Calculations ---
        direct_labor_cost = labor_hours * labor_rate
        cogs_per_unit = cost_materials + direct_labor_cost + packaging_cost + shipping_cost
        overhead_per_unit = monthly_overhead / monthly_production_volume
        fully_loaded_cost = cogs_per_unit + overhead_per_unit

        # --- Pass data to the next module via URL parameters ---
        return redirect(url_for('module2_market_analyzer', 
                                loaded_cost=fully_loaded_cost,
                                cogs=cogs_per_unit,
                                overhead=monthly_overhead))

    return render_template('noindex.html')


@app.route('/market-analysis', methods=['GET', 'POST'])
def module2_market_analyzer():
    """Module 2: Analyze the competitive landscape."""
    # Retrieve cost data from Module 1
    fully_loaded_cost = to_float(request.args.get('loaded_cost'))
    cogs = to_float(request.args.get('cogs'))
    monthly_overhead = to_float(request.args.get('overhead'))

    if request.method == 'POST':
        # --- Collect competitor data ---
        competitors = []
        for i in range(1, 4): # Assuming max 3 competitors for simplicity
            name = request.form.get(f'comp_name_{i}')
            price = to_float(request.form.get(f'comp_price_{i}'))
            if name and price > 0:
                competitors.append({'name': name, 'price': price})
        # --- Pass all collected data to Module 3 ---
        # We'll use a mix of URL params and form submission to the next step
        # For simplicity here, we'll re-render a page that posts to the next step
        return redirect(url_for('module3_strategy_modeler',
                                loaded_cost=fully_loaded_cost,
                                cogs=cogs,
                                overhead=monthly_overhead,
                                **{f'comp_price_{i+1}': c['price'] for i, c in enumerate(competitors)}))
    return render_template('module2.html', loaded_cost=fully_loaded_cost)


@app.route('/pricing-strategy', methods=['GET'])
def module3_strategy_modeler():
    """Module 3: Generate and display pricing strategies."""
    # --- Retrieve all data from previous modules ---
    fully_loaded_cost = to_float(request.args.get('loaded_cost'))
    cogs = to_float(request.args.get('cogs'))
    monthly_overhead = to_float(request.args.get('overhead'))
    
    comp_prices = []
    for i in range(1, 4):
        price = to_float(request.args.get(f'comp_price_{i}'))
        if price > 0:
            comp_prices.append(price)

    # --- Calculations for Module 3 ---
    # Market Analysis
    market_avg_price = sum(comp_prices) / len(comp_prices) if comp_prices else 0
    
    # Pricing Models (using a default 40% margin for Cost-Plus)
    desired_margin = 0.40
    cost_plus_price = fully_loaded_cost * (1 + desired_margin)
    
    penetration_price = market_avg_price * 0.90 if market_avg_price > 0 else 0
    premium_price = market_avg_price * 1.25 if market_avg_price > 0 else 0

    strategies = []

    # Function to calculate break-even units
    def get_breakeven(price):
        profit_per_unit = price - cogs
        if profit_per_unit <= 0:
            return 'N/A'
        return round(monthly_overhead / profit_per_unit)

    # Populate strategies
    strategies.append({
        'name': f'Cost-Plus ({desired_margin:.0%})',
        'price': cost_plus_price,
        'profit_per_unit': cost_plus_price - fully_loaded_cost,
        'breakeven_units': get_breakeven(cost_plus_price)
    })
    if market_avg_price > 0:
        strategies.append({
            'name': 'Market Average',
            'price': market_avg_price,
            'profit_per_unit': market_avg_price - fully_loaded_cost,
            'breakeven_units': get_breakeven(market_avg_price)
        })
        strategies.append({
            'name': 'Penetration (10% Below Avg)',
            'price': penetration_price,
            'profit_per_unit': penetration_price - fully_loaded_cost,
            'breakeven_units': get_breakeven(penetration_price)
        })
        strategies.append({
            'name': 'Premium (25% Above Avg)',
            'price': premium_price,
            'profit_per_unit': premium_price - fully_loaded_cost,
            'breakeven_units': get_breakeven(premium_price)
        })

    return render_template('module3.html', 
                           strategies=strategies, 
                           loaded_cost=fully_loaded_cost,
                           cogs=cogs)


@app.route('/optimization-simulator', methods=['GET', 'POST'])
def module4_optimization_simulator():
    """Module 4: "What-If" analysis simulator."""
    results = None
    if request.method == 'POST':
        # --- Get original and new values from the form ---
        original_cogs = to_float(request.form.get('original_cogs'))
        original_price = to_float(request.form.get('original_price'))
        
        new_cogs = to_float(request.form.get('new_cogs'))
        new_price = to_float(request.form.get('new_price'))
        projected_volume = to_float(request.form.get('projected_volume'))
        if projected_volume == 0:
            projected_volume = 1

        # --- Calculate "before" and "after" scenarios ---
        original_profit_per_unit = original_price - original_cogs
        new_profit_per_unit = new_price - new_cogs
        
        # We don't have original volume, so we can only show profit per unit
        # and projected total profit for the new scenario.
        new_total_profit = new_profit_per_unit * projected_volume
        
        results = {
            'original_profit_per_unit': original_profit_per_unit,
            'new_profit_per_unit': new_profit_per_unit,
            'new_total_profit': new_total_profit
        }

    # For the GET request, or to show the form again after POST
    # We need to get some base data to populate the form
    loaded_cost = to_float(request.args.get('loaded_cost'))
    cogs = to_float(request.args.get('cogs'))

    return render_template('module4.html', 
                           loaded_cost=loaded_cost, 
                           cogs=cogs, 
                           results=results)


if __name__ == '__main__':
    app.run(debug=True)