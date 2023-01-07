from flask import Flask, request, abort, render_template, redirect
from exchange import Exchange, hash_api_key
from decimal import Decimal
from db import RateLimit, User, OrderType, Referrer
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from env import DB
from time import time
from assets import assets
from math import floor
import re

app = Flask(__name__)
exchange = Exchange(DB)
engine = create_engine(DB)

@app.template_filter()
def format_decimal(d, decimal_places):
  digit = Decimal('10')
  while digit <= d:
    digit *= 10
  result = ''
  while decimal_places:
    result += str(floor(d % digit * 10 / digit))
    digit /= 10
    if digit == 1:
      result += '.'
    if digit < 1:
      decimal_places -= 1
  return result

@app.route('/api')
def api():
  return render_template('api.html')

@app.route('/', methods=['GET', 'POST'])
def auto_buy():
  try:
    referrer_hostname = re.match('https?://([^/]*)', request.referrer).group(1)()
  except:
    referrer_hostname = 'unknown'
  with Session(engine) as session:
    try:
      [ref] = session.query(Referrer).where(Referrer.hostname == referrer_hostname)
      ref.count += 1
      session.commit()
    except:
      session.add(Referrer(hostname=referrer_hostname, count=1))
      session.commit()
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
  return redirect('/auto/buy/%s' % auto)

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
  return redirect('/auto/sell/%s' % auto)

@app.get('/auto/buy/<id>')
def auto_buy_id(id):
  auto, unconfirmed_transactions = exchange.get_auto(id)
  if not auto:
    abort(404)
  return render_template('auto_buy.html', address=auto, unconfirmed_transactions=unconfirmed_transactions)

@app.get('/auto/sell/<id>')
def auto_sell_id(id):
  auto, unconfirmed_transactions = exchange.get_auto(id)
  if not auto:
    abort(404)
  return render_template('auto_sell.html', address=auto, unconfirmed_transactions=unconfirmed_transactions)

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
    return {'error': 'Invalid amount'}
  return exchange.withdraw(request.args['api_key'], request.args['currency'], request.args['address'], amount)

@app.route('/buy')
def buy():
  rate_limit()
  try:
    amount = Decimal(request.args['amount'])
  except:
    return {'error': 'Invalid amount'}
  try:
    price = Decimal(request.args['price'])
  except:
    return {'error': 'Invalid price'}
  return exchange.buy(request.args['api_key'], amount, price)

@app.route('/sell')
def sell():
  rate_limit()
  try:
    amount = Decimal(request.args['amount'])
  except:
    return {'error': 'Invalid amount'}
  try:
    price = Decimal(request.args['price'])
  except:
    return {'error': 'Invalid price'}
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
