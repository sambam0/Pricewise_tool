# Flask application for a four-step service pricing tool.
# 1. Job cost: fully loaded cost of delivering one job.
# 2. Market: competitor quotes for a similar job.
# 3. Price: cost-plus, market, penetration, and premium prices.
# 4. What-if: direct cost, price, and jobs per month.


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
    """Module 1: Calculate the fully loaded cost of delivering one job."""
    if request.method == 'POST':
        # Direct costs for one job
        cost_materials = to_float(request.form.get('cost_materials'))
        labor_hours = to_float(request.form.get('labor_hours'))
        labor_rate = to_float(request.form.get('labor_rate'))
        packaging_cost = to_float(request.form.get('packaging_cost'))
        shipping_cost = to_float(request.form.get('shipping_cost'))

        # Overhead spread across the jobs delivered in a month
        monthly_overhead = to_float(request.form.get('monthly_overhead'))
        monthly_production_volume = to_float(request.form.get('monthly_production_volume'))
        if monthly_production_volume == 0:
            monthly_production_volume = 1 # Avoid division by zero

        direct_labor_cost = labor_hours * labor_rate
        cogs_per_unit = cost_materials + direct_labor_cost + packaging_cost + shipping_cost
        overhead_per_unit = monthly_overhead / monthly_production_volume
        fully_loaded_cost = cogs_per_unit + overhead_per_unit

        return redirect(url_for('module2_market_analyzer',
                                loaded_cost=fully_loaded_cost,
                                cogs=cogs_per_unit,
                                overhead=monthly_overhead))

    return render_template('module1.html')


@app.route('/market-analysis', methods=['GET', 'POST'])
def module2_market_analyzer():
    """Module 2: Collect competitor quotes for a similar job."""
    fully_loaded_cost = to_float(request.args.get('loaded_cost'))
    cogs = to_float(request.args.get('cogs'))
    monthly_overhead = to_float(request.args.get('overhead'))

    if request.method == 'POST':
        competitors = []
        for i in range(1, 4):
            name = (request.form.get(f'comp_name_{i}') or '').strip()
            price = to_float(request.form.get(f'comp_price_{i}'))
            if name and price > 0:
                competitors.append({'name': name, 'price': price})
        quote_params = {}
        for i, competitor in enumerate(competitors):
            quote_params[f'comp_price_{i+1}'] = competitor['price']
            quote_params[f'comp_name_{i+1}'] = competitor['name']
        return redirect(url_for('module3_strategy_modeler',
                                loaded_cost=fully_loaded_cost,
                                cogs=cogs,
                                overhead=monthly_overhead,
                                **quote_params))
    return render_template('module2.html',
                           loaded_cost=fully_loaded_cost,
                           cogs=cogs,
                           overhead=monthly_overhead)


@app.route('/pricing-strategy', methods=['GET'])
def module3_strategy_modeler():
    """Module 3: Generate and display pricing strategies."""
    fully_loaded_cost = to_float(request.args.get('loaded_cost'))
    cogs = to_float(request.args.get('cogs'))
    monthly_overhead = to_float(request.args.get('overhead'))

    competitors = []
    comp_prices = []
    for i in range(1, 4):
        price = to_float(request.args.get(f'comp_price_{i}'))
        name = (request.args.get(f'comp_name_{i}') or '').strip()
        if price > 0:
            competitors.append({'name': name, 'price': price})
            comp_prices.append(price)

    market_avg_price = sum(comp_prices) / len(comp_prices) if comp_prices else 0

    # Pricing models (using a default 40% margin for Cost-Plus)
    desired_margin = 0.40
    cost_plus_price = fully_loaded_cost * (1 + desired_margin)

    penetration_price = market_avg_price * 0.90 if market_avg_price > 0 else 0
    premium_price = market_avg_price * 1.25 if market_avg_price > 0 else 0

    strategies = []

    def get_breakeven(price):
        profit_per_unit = price - cogs
        if profit_per_unit <= 0:
            return 'N/A'
        return round(monthly_overhead / profit_per_unit)

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
                           competitors=competitors,
                           loaded_cost=fully_loaded_cost,
                           cogs=cogs)


@app.route('/optimization-simulator', methods=['GET', 'POST'])
def module4_optimization_simulator():
    """Module 4: What-if analysis for direct cost, price, and jobs per month."""
    results = None
    if request.method == 'POST':
        original_cogs = to_float(request.form.get('original_cogs'))
        original_price = to_float(request.form.get('original_price'))

        new_cogs = to_float(request.form.get('new_cogs'))
        new_price = to_float(request.form.get('new_price'))
        projected_volume = to_float(request.form.get('projected_volume'))
        if projected_volume == 0:
            projected_volume = 1

        original_profit_per_unit = original_price - original_cogs
        new_profit_per_unit = new_price - new_cogs
        new_total_profit = new_profit_per_unit * projected_volume

        results = {
            'original_profit_per_unit': original_profit_per_unit,
            'new_profit_per_unit': new_profit_per_unit,
            'new_total_profit': new_total_profit
        }
        loaded_cost = to_float(request.form.get('loaded_cost') or request.args.get('loaded_cost'))
        cogs = to_float(request.form.get('original_cogs') or request.args.get('cogs'))
        entered = {
            'original_price': request.form.get('original_price', ''),
            'new_cogs': request.form.get('new_cogs', ''),
            'new_price': request.form.get('new_price', ''),
            'projected_volume': request.form.get('projected_volume', ''),
        }
    else:
        loaded_cost = to_float(request.args.get('loaded_cost'))
        cogs = to_float(request.args.get('cogs'))
        entered = {
            'original_price': '',
            'new_cogs': f'{cogs:.2f}' if cogs else '',
            'new_price': '',
            'projected_volume': '',
        }

    return render_template('module4.html',
                           loaded_cost=loaded_cost,
                           cogs=cogs,
                           entered=entered,
                           results=results)


if __name__ == '__main__':
    app.run(debug=True)
