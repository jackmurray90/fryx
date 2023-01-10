from flask import Flask, request, abort, render_template, redirect
from exchange import Exchange
from decimal import Decimal
from db import OrderType, Referrer
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from env import DB
from assets import assets
from math import floor
from dashboard import dashboard
from csrf import csrf
from rate_limit import rate_limit
from datetime import datetime
import re

app = Flask(__name__)
exchange = Exchange(DB)
engine = create_engine(DB)
get, post = csrf(app, exchange)

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

@app.template_filter()
def timestamp(t):
  return datetime.fromtimestamp(t).strftime('%Y-%m-%d %H:%M:%S UTC')

dashboard(app, exchange, engine)

@get('/api')
def api(csrf, logged_in):
  rate_limit(engine, ip=True)
  log_referrer()
  return render_template('api.html', csrf=csrf, logged_in=logged_in)

@get('/')
def xmr_buy(csrf, logged_in):
  rate_limit(engine, ip=True)
  log_referrer()
  return render_template('buy.html', csrf=csrf, logged_in=logged_in)

@post('/')
def xmr_buy_action(csrf, logged_in):
  rate_limit(engine, ip=True)
  auto = exchange.auto_buy(request.form['market'], request.form['withdrawal_address'], request.form['refund_address'])
  if 'error' in auto:
    return render_template('buy.html', order_type='buy', error=auto['error'], csrf=csrf, logged_in=logged_in)
  return redirect('/auto/buy/%s' % auto['id'])

@get('/xmr/sell')
def xmr_sell(csrf, logged_in):
  rate_limit(engine, ip=True)
  log_referrer()
  return render_template('sell.html', csrf=csrf, logged_in=logged_in)

@post('/xmr/sell')
def xmr_sell_action(csrf, logged_in):
  rate_limit(engine, ip=True)
  auto = exchange.auto_sell(request.form['market'], request.form['withdrawal_address'], request.form['refund_address'])
  if 'error' in auto:
    return render_template('sell.html', order_type='sell', error=auto['error'], csrf=csrf, logged_in=logged_in)
  return redirect('/auto/sell/%s' % auto['id'])

@get('/auto/buy/<id>')
def auto_buy_id(csrf, logged_in, id):
  rate_limit(engine, ip=True)
  if 'amount' in request.args:
    try:
      amount = Decimal(request.args['amount'])
    except:
      return {'error': 'Please enter a decimal value.'}
  else:
    amount = None
  try:
    address, unconfirmed_transactions, confirmed_deposits, approximate_cost = exchange.get_auto(id, amount)
  except:
    abort(404)
  return render_template('auto_buy.html', address=address, unconfirmed_transactions=unconfirmed_transactions, confirmed_deposits=confirmed_deposits, error=approximate_cost.get('error'), amount=approximate_cost.get('amount'), approximate_cost=approximate_cost.get('cost'), hit_maximum=approximate_cost.get('hit_maximum'), csrf=csrf, logged_in=logged_in)

@get('/auto/sell/<id>')
def auto_sell_id(csrf, logged_in, id):
  rate_limit(engine, ip=True)
  if 'amount' in request.args:
    try:
      amount = Decimal(request.args['amount'])
    except:
      return {'error': 'Please enter a decimal value.'}
  else:
    amount = None
  try:
    address, unconfirmed_transactions, confirmed_deposits, approximate_value = exchange.get_auto(id, amount)
  except:
    abort(404)
  return render_template('auto_sell.html', address=address, unconfirmed_transactions=unconfirmed_transactions, confirmed_deposits=confirmed_deposits, error=approximate_value.get('error'), amount=approximate_value.get('amount'), approximate_value=approximate_value.get('value'), hit_maximum=approximate_value.get('hit_maximum'), csrf=csrf, logged_in=logged_in)

@app.route('/order_book')
def order_book():
  rate_limit(engine, ip=True)
  return exchange.order_book(request.args['market'])

@app.route('/new_user')
def new_user():
  rate_limit(engine, ip=True)
  return exchange.new_user()

@app.route('/balances')
def balances():
  rate_limit(engine)
  return exchange.balances(request.args['api_key'])

@app.route('/orders')
def orders():
  rate_limit(engine)
  return exchange.orders(request.args['api_key'], request.args['market'])

@app.route('/trades')
def trades():
  rate_limit(engine)
  return exchange.trades(request.args['api_key'], request.args['market'])

@app.route('/deposit')
def deposit():
  rate_limit(engine)
  return exchange.deposit(request.args['api_key'], request.args['asset'])

@app.route('/withdraw')
def withdraw():
  rate_limit(engine)
  try:
    amount = Decimal(request.args['amount'])
  except:
    return {'error': 'Invalid amount'}
  return exchange.withdraw(request.args['api_key'], request.args['asset'], request.args['address'], amount)

@app.route('/buy')
def buy():
  rate_limit(engine)
  try:
    volume = Decimal(request.args['volume'])
  except:
    return {'error': 'Invalid volume'}
  try:
    price = Decimal(request.args['price'])
  except:
    return {'error': 'Invalid price'}
  return exchange.buy(request.args['api_key'], request.args['market'], volume, price)

@app.route('/sell')
def sell():
  rate_limit(engine)
  try:
    volume = Decimal(request.args['volume'])
  except:
    return {'error': 'Invalid volume'}
  try:
    price = Decimal(request.args['price'])
  except:
    return {'error': 'Invalid price'}
  return exchange.sell(request.args['api_key'], request.args['market'], volume, price)

@app.route('/cancel')
def cancel():
  rate_limit(engine)
  return exchange.cancel(request.args['api_key'], request.args['order_id'])

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
