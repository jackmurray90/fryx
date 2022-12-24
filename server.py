from flask import Flask, request
from exchange import Exchange
from decimal import Decimal

app = Flask(__name__)

exchange = Exchange('postgresql://:@localhost/tradeapi')

@app.route('/new_user')
def new_user():
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
