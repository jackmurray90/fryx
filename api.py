from flask import Flask, request, abort, render_template
from exchange import Exchange, hash_api_key
from decimal import Decimal
from db import RateLimit, User
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from env import DB
from time import time

app = Flask(__name__)
exchange = Exchange(DB)
engine = create_engine(DB)

@app.route('/')
def api():
  return render_template('api.html')

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
    if rate_limit.timestamp + 1 > time():
      abort(429)
    rate_limit.timestamp = time()
    session.commit()

@app.route('/new_user')
def new_user():
  rate_limit(ip=True)
  return exchange.new_user()

@app.route('/markets')
def markets():
  rate_limit(ip=True)
  return exchange.markets()

@app.route('/balance')
def balance():
  rate_limit()
  bal = exchange.balance(request.args['api_key'], request.args.get('asset'))
  if isinstance(bal, Decimal):
    return '%0.18f' % bal
  return bal

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
  return exchange.deposit(request.args['api_key'], request.args['asset'])

@app.route('/withdraw')
def withdraw():
  rate_limit()
  try:
    amount = Decimal(request['amount'])
  except:
    return 'Invalid amount'
  return exchange.withdraw(request.args['api_key'], request.args['asset'], request.args['address'], amount)

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
  return exchange.buy(request.args['api_key'], request.args['asset'], request.args['currency'], amount, price)

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
  return exchange.sell(request.args['api_key'], request.args['asset'], request.args['currency'], amount, price)

@app.route('/cancel')
def cancel():
  rate_limit()
  return exchange.cancel(request.args['api_key'], request.args['order_id'])
