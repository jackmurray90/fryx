from flask import Flask, request, render_template, abort
from exchange import Exchange
from decimal import Decimal
from json import loads
from env import RECAPTCHA_SECRET, DB
import urllib

app = Flask(__name__)

exchange = Exchange(DB)

@app.route('/')
def index():
  return render_template('index.html')

def get_new_user_api_key():
  data = urllib.parse.urlencode({
    'secret': RECAPTCHA_SECRET,
    'response': request.args['g-recaptcha-response'],
    'remoteip': request.remote_addr
    }).encode()
  req =  urllib.request.Request('https://www.google.com/recaptcha/api/siteverify', data=data)
  with urllib.request.urlopen(req) as response:
    encoding = response.info().get_content_charset('utf-8')
    data = loads(response.read().decode(encoding))
    if data['success'] and data['hostname'].endswith('tradeapi.net'):
      return exchange.new_user()
  return None

@app.route('/new_user_html')
def new_user_html():
  api_key = get_new_user_api_key()
  if api_key is None:
    return render_template('index.html')
  return render_template('index.html', api_key=exchange.new_user())

@app.route('/new_user')
def new_user():
  api_key = get_new_user_api_key()
  if api_key is None:
    abort(503)
  return exchange.new_user()

@app.route('/balance')
def balance():
  return exchange.balance(request.args['api_key'], request.args['asset'])

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
