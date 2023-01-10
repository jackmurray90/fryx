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
  if d == None:
    return ''
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
  rate_limit(ip=True)
  log_referrer()
  return render_template('api.html')

@app.route('/', methods=['GET', 'POST'])
def xmr_buy():
  rate_limit(ip=True)
  log_referrer()
  if not 'withdrawal_address' in request.form:
    return render_template('buy.html')
  auto = exchange.auto_buy(request.form['market'], request.form['withdrawal_address'], request.form['refund_address'])
  if 'error' in auto:
    return render_template('buy.html', order_type='buy', error=auto['error'])
  return redirect('/auto/buy/%s' % auto['id'])

@app.route('/xmr/sell', methods=['GET', 'POST'])
def xmr_sell():
  rate_limit(ip=True)
  log_referrer()
  if not 'withdrawal_address' in request.form:
    return render_template('sell.html')
  auto = exchange.auto_sell(request.form['market'], request.form['withdrawal_address'], request.form['refund_address'])
  if 'error' in auto:
    return render_template('sell.html', order_type='sell', error=auto['error'])
  return redirect('/auto/sell/%s' % auto['id'])

@app.get('/auto/buy/<id>')
def auto_buy_id(id):
  rate_limit(ip=True)
  try:
    address, unconfirmed_transactions, confirmed_deposits, approximate_cost = exchange.get_auto(id, request.args.get('amount'))
  except:
    abort(404)
  return render_template('auto_buy.html', address=address, unconfirmed_transactions=unconfirmed_transactions, confirmed_deposits=confirmed_deposits, error=approximate_cost.get('error'), amount=approximate_cost.get('amount'), approximate_cost=approximate_cost.get('cost'), hit_maximum=approximate_cost.get('hit_maximum'))

@app.get('/auto/sell/<id>')
def auto_sell_id(id):
  rate_limit(ip=True)
  try:
    address, unconfirmed_transactions, confirmed_deposits, approximate_value = exchange.get_auto(id, request.args.get('amount'))
  except:
    abort(404)
  return render_template('auto_sell.html', address=address, unconfirmed_transactions=unconfirmed_transactions, confirmed_deposits=confirmed_deposits, error=approximate_value.get('error'), amount=approximate_value.get('amount'), approximate_value=approximate_value.get('value'), hit_maximum=approximate_value.get('hit_maximum'))

@app.route('/order_book')
def order_book():
  rate_limit(ip=True)
  return exchange.order_book(request.args['market'])

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
  return exchange.orders(request.args['api_key'], request.args['market'])

@app.route('/trades')
def trades():
  rate_limit()
  return exchange.trades(request.args['api_key'], request.args['market'])

@app.route('/deposit')
def deposit():
  rate_limit()
  return exchange.deposit(request.args['api_key'], request.args['asset'])

@app.route('/withdraw')
def withdraw():
  rate_limit()
  try:
    amount = Decimal(request.args['amount'])
  except:
    return {'error': 'Invalid amount'}
  return exchange.withdraw(request.args['api_key'], request.args['asset'], request.args['address'], amount)

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
  return exchange.buy(request.args['api_key'], request.args['market'], amount, price)

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
  return exchange.sell(request.args['api_key'], request.args['market'], amount, price)

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
      rate_limit = RateLimit(address=address, timestamps='')
      session.add(rate_limit)
      session.commit()
    timestamps = [float(t) for t in rate_limit.timestamps.split() if float(t) >= time()-1]
    if len(timestamps) > 50:
      abort(429)
    timestamps.append(time())
    rate_limit.timestamps = ' '.join([str(t) for t in timestamps])
    session.commit()

def log_referrer():
  try:
    referrer_hostname = re.match('https?://([^/]*)', request.referrer).group(1)
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
