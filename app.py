from flask import Flask, request, abort, render_template, redirect
from exchange import Exchange, hash_api_key
from decimal import Decimal
from db import RateLimit, User, OrderType
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from env import DB
from time import time
from assets import assets

app = Flask(__name__)
exchange = Exchange(DB)
engine = create_engine(DB)

@app.route('/')
def index():
  with Session(engine) as session:
    return render_template('index.html')

@app.route('/api')
def api():
  return render_template('api.html')

@app.route('/auto/buy', methods=['GET', 'POST'])
def auto_buy():
  if not 'monero_address' in request.form:
    return render_template('buy.html')
  errors = []
  if not assets['BTC'].validate_address(request.form['bitcoin_address']):
    errors.append('Invalid bitcoin address.')
  if not assets['XMR'].validate_address(request.form['monero_address']):
    errors.append('Invalid monero address.')
  if errors:
    return render_template('buy.html', errors=errors)
  auto = exchange.auto(OrderType.BUY, request.form['monero_address'], request.form['bitcoin_address'])
  if not auto:
    errors = ['One of your addresses has been used on this site before. Please use a new addresses.']
    return render_template('buy.html', errors=errors)
  return redirect('/auto/%s' % auto)

@app.route('/auto/sell', methods=['GET', 'POST'])
def auto_sell():
  if not 'bitcoin_address' in request.form:
    return render_template('sell.html')
  errors = []
  if not assets['BTC'].validate_address(request.form['bitcoin_address']):
    errors.append('Invalid bitcoin address.')
  if not assets['XMR'].validate_address(request.form['monero_address']):
    errors.append('Invalid monero address.')
  if errors:
    return render_template('sell.html', errors=errors)
  auto = exchange.auto(OrderType.SELL, request.form['bitcoin_address'], request.form['monero_address'])
  if not auto:
    errors = ['One of your addresses has been used on this site before. Please use a new addresses.']
    return render_template('buy.html', errors=errors)
  return redirect('/auto/%s' % auto)

@app.get('/auto/<id>')
def auto(id):
  auto = exchange.get_auto(id)
  if not auto:
    abort(404)
  return render_template('auto.html', address=auto)

@app.route('/order_book')
def order_book():
  rate_limit(ip=True)
  return exchange.order_book()

@app.route('/new_user')
def new_user():
  rate_limit(ip=True)
  return exchange.new_user()

@app.route('/balances')
def balances():
  rate_limit()
  return exchange.balances(request.args['api_key'])

@app.route('/orders')
def orders():
  rate_limit()
  return exchange.orders(request.args['api_key'])

@app.route('/trades')
def trades():
  rate_limit()
  return exchange.trades(request.args['api_key'])

@app.route('/deposit')
def deposit():
  rate_limit()
  return exchange.deposit(request.args['api_key'], request.args['currency'])

@app.route('/withdraw')
def withdraw():
  rate_limit()
  try:
    amount = Decimal(request['amount'])
  except:
    return 'Invalid amount'
  return exchange.withdraw(request.args['api_key'], request.args['currency'], request.args['address'], amount)

@app.route('/buy')
def buy():
  rate_limit()
  try:
    amount = Decimal(request['amount'])
  except:
    return 'Invalid amount'
  try:
    price = Decimal(request['price'])
  except:
    return 'Invalid price'
  return exchange.buy(request.args['api_key'], amount, price)

@app.route('/sell')
def sell():
  rate_limit()
  try:
    amount = Decimal(request['amount'])
  except:
    return 'Invalid amount'
  try:
    price = Decimal(request['price'])
  except:
    return 'Invalid price'
  return exchange.sell(request.args['api_key'], amount, price)

@app.route('/cancel')
def cancel():
  rate_limit()
  return exchange.cancel(request.args['api_key'], request.args['order_id'])

def rate_limit(ip=False):
  with Session(engine) as session:
    if ip:
      address = request.remote_addr
    else:
      try:
        [user] = session.query(User).where(User.api_key == hash_api_key(request.args['api_key']))
        address = request.args['api_key']
      except:
        abort(403)
    try:
      [rate_limit] = session.query(RateLimit).where(RateLimit.address == address)
    except:
      rate_limit = RateLimit(address=address, timestamp=0)
      session.add(rate_limit)
      session.commit()
    if rate_limit.timestamp + Decimal('0.5') > time():
      abort(429)
    rate_limit.timestamp = time()
    session.commit()
