# Flask application for a service pricing tool.
# 1. Your numbers: cost of one job, today's price, margin, and demand.
# 2. Quotes: up to three competitor prices.
# 3. Result: one starting price and how it compares with today.


from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

def to_float(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0

def whole_number(value):
    if float(value).is_integer():
        return int(value)
    return value

def read_situation():
    """Answers carried from the first page through the quote step."""
    margin_percent = to_float(request.values.get('margin'))
    if margin_percent < 0:
        margin_percent = 0
    demand = request.values.get('demand')
    if demand not in ('need_work', 'booked'):
        demand = 'need_work'
    return {
        'jobs': to_float(request.values.get('jobs')),
        'current_price': to_float(request.values.get('current_price')),
        'margin': margin_percent,
        'demand': demand,
    }

@app.route('/', methods=['GET', 'POST'])
def module1_cost_calculator():
    """Collect the cost of one job and the answers that choose a starting price."""
    if request.method == 'POST':
        cost_materials = to_float(request.form.get('cost_materials'))
        labor_hours = to_float(request.form.get('labor_hours'))
        labor_rate = to_float(request.form.get('labor_rate'))
        packaging_cost = to_float(request.form.get('packaging_cost'))
        shipping_cost = to_float(request.form.get('shipping_cost'))

        monthly_overhead = to_float(request.form.get('monthly_overhead'))
        jobs = to_float(request.form.get('monthly_production_volume'))
        if jobs == 0:
            jobs = 1

        direct_labor_cost = labor_hours * labor_rate
        cogs_per_unit = cost_materials + direct_labor_cost + packaging_cost + shipping_cost
        overhead_per_unit = monthly_overhead / jobs
        fully_loaded_cost = cogs_per_unit + overhead_per_unit

        margin_percent = to_float(request.form.get('margin'))
        if margin_percent < 0:
            margin_percent = 0
        demand = request.form.get('demand')
        if demand not in ('need_work', 'booked'):
            demand = 'need_work'

        return redirect(url_for('module2_market_analyzer',
                                loaded_cost=fully_loaded_cost,
                                cogs=cogs_per_unit,
                                overhead=monthly_overhead,
                                jobs=jobs,
                                current_price=to_float(request.form.get('current_price')),
                                margin=margin_percent,
                                demand=demand))

    return render_template('module1.html')


@app.route('/market-analysis', methods=['GET', 'POST'])
def module2_market_analyzer():
    """Collect competitor quotes and carry the first-page answers forward."""
    fully_loaded_cost = to_float(request.args.get('loaded_cost'))
    cogs = to_float(request.args.get('cogs'))
    monthly_overhead = to_float(request.args.get('overhead'))
    situation = read_situation()

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
                                jobs=situation['jobs'],
                                current_price=situation['current_price'],
                                margin=situation['margin'],
                                demand=situation['demand'],
                                **quote_params))
    return render_template('module2.html',
                           loaded_cost=fully_loaded_cost,
                           cogs=cogs,
                           overhead=monthly_overhead,
                           **situation)


@app.route('/pricing-strategy', methods=['GET'])
def module3_strategy_modeler():
    """Show one starting price and the other prices beside it."""
    fully_loaded_cost = to_float(request.args.get('loaded_cost'))
    cogs = to_float(request.args.get('cogs'))
    monthly_overhead = to_float(request.args.get('overhead'))
    situation = read_situation()
    jobs = situation['jobs'] if situation['jobs'] > 0 else 1
    current_price = situation['current_price']
    margin_percent = situation['margin']
    desired_margin = margin_percent / 100

    competitors = []
    comp_prices = []
    for i in range(1, 4):
        price = to_float(request.args.get(f'comp_price_{i}'))
        name = (request.args.get(f'comp_name_{i}') or '').strip()
        if price > 0:
            competitors.append({'name': name, 'price': price})
            comp_prices.append(price)

    market_avg_price = sum(comp_prices) / len(comp_prices) if comp_prices else 0
    cost_plus_price = fully_loaded_cost * (1 + desired_margin)
    penetration_price = market_avg_price * 0.90 if market_avg_price > 0 else 0
    premium_price = market_avg_price * 1.25 if market_avg_price > 0 else 0

    def get_breakeven(price):
        profit_per_unit = price - cogs
        if profit_per_unit <= 0:
            return None
        return round(monthly_overhead / profit_per_unit)

    margin_label = f'{whole_number(margin_percent)}%'
    strategies = [{
        'key': 'cost_plus',
        'name': f'Cost-Plus ({margin_label})',
        'price': cost_plus_price,
        'profit_per_unit': cost_plus_price - fully_loaded_cost,
        'breakeven_units': get_breakeven(cost_plus_price),
    }]
    if market_avg_price > 0:
        strategies.extend([
            {
                'key': 'market',
                'name': 'Market Average',
                'price': market_avg_price,
                'profit_per_unit': market_avg_price - fully_loaded_cost,
                'breakeven_units': get_breakeven(market_avg_price),
            },
            {
                'key': 'penetration',
                'name': 'Penetration (10% Below Avg)',
                'price': penetration_price,
                'profit_per_unit': penetration_price - fully_loaded_cost,
                'breakeven_units': get_breakeven(penetration_price),
            },
            {
                'key': 'premium',
                'name': 'Premium (25% Above Avg)',
                'price': premium_price,
                'profit_per_unit': premium_price - fully_loaded_cost,
                'breakeven_units': get_breakeven(premium_price),
            },
        ])

    if market_avg_price <= 0:
        starting_key = 'cost_plus'
        reason = 'No comparable quotes, so start with your cost plus the margin you chose.'
    elif situation['demand'] == 'booked':
        starting_key = 'premium'
        reason = 'You are booked, so start above the average quote.'
    else:
        starting_key = 'penetration'
        reason = 'You need more work, so start just under the average quote.'

    starting = next(strategy for strategy in strategies if strategy['key'] == starting_key)
    for strategy in strategies:
        strategy['starting'] = strategy['key'] == starting_key
        if strategy['breakeven_units'] is None:
            strategy['breakeven_units'] = 'N/A'

    gap_per_job = starting['price'] - current_price
    gap_per_month = gap_per_job * jobs
    if abs(gap_per_job) < 0.005:
        gap_per_job = 0
        gap_per_month = 0
    jobs_needed = get_breakeven(starting['price'])
    capacity = None
    if jobs_needed is not None and jobs_needed > jobs:
        capacity = {
            'needed': jobs_needed,
            'can_deliver': whole_number(jobs),
        }

    return render_template('module3.html',
                           strategies=strategies,
                           competitors=competitors,
                           loaded_cost=fully_loaded_cost,
                           current_price=current_price,
                           jobs=whole_number(jobs),
                           starting=starting,
                           reason=reason,
                           starting_below_cost=starting['price'] < fully_loaded_cost,
                           current_below_cost=current_price < fully_loaded_cost,
                           gap_per_job=gap_per_job,
                           gap_per_month=gap_per_month,
                           capacity=capacity)


if __name__ == '__main__':
    app.run(debug=True)
