from flask import request, abort
from decimal import Decimal
from json import loads
from env import RECAPTCHA_SECRET
import urllib

def get_new_user_api_key(exchange):
  data = urllib.parse.urlencode({
    'secret': RECAPTCHA_SECRET,
    'response': request.form['g-recaptcha-response'],
    'remoteip': request.remote_addr
    }).encode()
  req =  urllib.request.Request('https://www.google.com/recaptcha/api/siteverify', data=data)
  with urllib.request.urlopen(req) as response:
    encoding = response.info().get_content_charset('utf-8')
    data = loads(response.read().decode(encoding))
    if data['success'] and data['hostname'].endswith('tradeapi.net'):
      return exchange.new_user()
  return None

def api(app, exchange):

  @app.route('/new_user')
  def new_user():
    api_key = get_new_user_api_key(exchange)
    if api_key is None:
      abort(503)
    return api_key

  @app.route('/markets')
  def markets():
    return exchange.markets()

  @app.route('/balance')
  def balance():
    return exchange.balance(request.args['api_key'], request.args['asset'])

  @app.route('/balances')
  def balances():
    return exchange.balances(request.args['api_key'])

  @app.route('/orders')
  def orders():
    return exchange.orders(request.args['api_key'])

  @app.route('/trades')
  def trades():
    return exchange.trades(request.args['api_key'])

  @app.route('/deposit')
  def deposit():
    return exchange.deposit(request.args['api_key'], request.args['asset'])

  @app.route('/withdraw')
  def withdraw():
    try:
      amount = Decimal(request['amount'])
    except:
      return 'Invalid amount'
    return exchange.withdraw(request.args['api_key'], request.args['asset'], request.args['address'], amount)

  @app.route('/buy')
  def buy():
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
    try:
      amount = Decimal(request['amount'])
    except:
      return 'Invalid amount'
    try:
      price = Decimal(request['price'])
    except:
      return 'Invalid price'
    return exchange.sell(request.args['api_key'], request.args['asset'], request.args['currency'], amount, price)
