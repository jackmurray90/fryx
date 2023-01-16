from flask import request, abort, redirect, make_response, render_template
from csrf import csrf
from db import User, LoginCode, Asset
from sqlalchemy.orm import Session
from exchange import random_128_bit_string
from mail import send_email
from rate_limit import rate_limit
from time import time
from urllib.parse import quote_plus
from decimal import Decimal
from assets import assets
import re

def dashboard(app, exchange, engine):
  get, post = csrf(app, exchange)

  @get('/dashboard/new_user')
  def new_user(render_template, user):
    rate_limit(engine, ip=True)
    if user: return redirect('/dashboard/balances')
    return render_template('dashboard/new_user.html')

  @post('/dashboard/new_user')
  def new_user(redirect, user):
    rate_limit(engine, ip=True)
    if user: return redirect('/dashboard/balances')
    if not re.match('^[\w.-]+@[\w.-]+$', request.form['email']):
      return redirect('/dashboard/new_user', 'Please enter a valid email address.')
    with Session(engine) as session:
      email_verification_code = random_128_bit_string()
      try:
        [user] = session.query(User).where(User.email == request.form['email'])
        return redirect('/dashboard/new_user', 'A user with that email address already exists.')
      except:
        pass
      user = User(email=request.form['email'], api_key=random_128_bit_string(), email_verification_code=email_verification_code)
      session.add(user)
      session.commit()
    send_email(request.form['email'], "Welcome to Fryx Finance", render_template('emails/email_verification.html', email_verification_code=email_verification_code))
    return redirect('/dashboard/check_verification_email')

  @get('/dashboard/check_verification_email')
  def check_email(render_template, user):
    rate_limit(engine, ip=True)
    if user: return redirect('/dashboard/balances')
    return render_template('dashboard/check_verification_email.html')

  @get('/dashboard/verify_email/<code>')
  def verify_email(render_template, user, code):
    rate_limit(engine, ip=True)
    with Session(engine) as session:
      try:
        [user] = session.query(User).where(User.email_verification_code == code)
      except:
        abort(404)
      user.email_verified = True
      user.email_verification_code = None
      session.commit()
      response = make_response(redirect('/dashboard/verified_email'))
      response.set_cookie('api_key', user.api_key)
      return response

  @get('/dashboard/verified_email')
  def verified_email(render_template, user):
    rate_limit(engine, ip=True)
    return render_template('dashboard/verified_email.html')

  @get('/dashboard/login')
  def login(render_template, user):
    rate_limit(engine, ip=True)
    if user: return redirect('/dashboard/balances')
    return render_template('dashboard/login.html')

  @post('/dashboard/login')
  def login(redirect, user):
    rate_limit(engine, ip=True)
    if user: return redirect('/dashboard/balances')
    with Session(engine) as session:
      try:
        [user] = session.query(User).where(User.email == request.form['email'])
      except:
        return redirect('/dashboard/login', 'User not found.')
      if not user.email_verified:
        return redirect('/dashboard/login', 'Please check your email for verification before logging in.')
      login_code = LoginCode(user_id=user.id, code=random_128_bit_string(), expiry=int(time() + 60*60*2))
      session.add(login_code)
      session.commit()
      send_email(user.email, "Login to Fryx Finance", render_template('emails/login.html', code=login_code.code))
      return redirect('/dashboard/check_login_email')

  @get('/dashboard/check_login_email')
  def check_login_email(render_template, user):
    rate_limit(engine, ip=True)
    if user: return redirect('/dashboard/balances')
    return render_template('dashboard/check_login_email.html')

  @get('/dashboard/login/<code>')
  def login(render_template, user, code):
    rate_limit(engine, ip=True)
    if user: return redirect('/dashboard/balances')
    with Session(engine) as session:
      try:
        [login_code] = session.query(LoginCode).where(LoginCode.code == code)
      except:
        abort(404)
      if login_code.expiry < time():
        return render_template('dashboard/login_code_expired.html')
      response = make_response(redirect('/dashboard/balances'))
      response.set_cookie('api_key', login_code.user.api_key)
      session.delete(login_code)
      session.commit()
      return response

  @post('/dashboard/logout')
  def logout(redirect, user):
    rate_limit(engine, ip=True)
    if not user: return redirect('/')
    response = redirect('/')
    response.set_cookie('api_key', '', expires=0)
    return response

  @get('/dashboard/balances')
  def balances(render_template, user):
    rate_limit(engine, ip=True)
    if not user: return redirect('/')
    return render_template('dashboard/balances.html', balances=exchange.balances(user.api_key))

  @get('/dashboard/orders/<market_name>')
  def orders(render_template, user, market_name):
    rate_limit(engine, ip=True)
    if not user: return redirect('/')
    market = exchange.check_market(market_name)
    if not market: abort(404)
    return render_template('dashboard/orders.html', market=market, orders=exchange.orders(user.api_key, market_name))

  @post('/dashboard/orders/<market_name>')
  def orders(redirect, user, market_name):
    rate_limit(engine, ip=True)
    if not user: return redirect('/')
    market = exchange.check_market(market_name)
    if not market: abort(404)
    try:
      volume = Decimal(request.form['volume'])
      price = Decimal(request.form['price'])
    except:
      return redirect(f'/dashboard/orders/{market_name}', 'Please enter only decimal values for volume and price.')
    if request.form['type'] == 'buy':
      new_order = exchange.buy(user.api_key, market_name, volume, price)
    else:
      new_order = exchange.sell(user.api_key, market_name, volume, price)
    if 'error' in new_order:
      return redirect(f'/dashboard/orders/{market_name}', new_order['error'])
    if 'success' in new_order:
      return redirect(f'/dashboard/orders/{market_name}', 'The order was filled.')
    return redirect(f'/dashboard/orders/{market_name}', f'A new order was created with order ID {new_order["order_id"]}.')

  @post('/dashboard/orders/<market_name>/cancel')
  def cancel(redirect, user, market_name):
    rate_limit(engine, ip=True)
    if not user: return redirect('/')
    market = exchange.check_market(market_name)
    if not market: abort(404)
    try:
      id = Decimal(request.form['id'])
    except:
      return redirect(f'/dashboard/orders/{market_name}', 'Invalid order id')
    result = exchange.cancel(user.api_key, id)
    if 'error' in result:
      return redirect(f'/dashboard/orders/{market_name}', result['error'])
    return redirect(f'/dashboard/orders/{market_name}', 'The order was cancelled.')

  @get('/dashboard/trades/<market_name>')
  def trades(render_template, user, market_name):
    rate_limit(engine, ip=True)
    if not user: return redirect('/')
    market = exchange.check_market(market_name)
    if not market: abort(404)
    return render_template('dashboard/trades.html', market=market, trades=exchange.trades(user.api_key, market_name))

  @get('/dashboard/deposit')
  def deposit(render_template, user):
    rate_limit(engine, ip=True)
    if not user: return redirect('/')
    with Session(engine) as session:
      coins = []
      unconfirmed_deposits = []
      for asset in session.query(Asset).all():
        address = exchange.deposit(user.api_key, asset.name)['address']
        coins.append({'name': asset.name, 'address': address})
        for deposit in assets[asset.name].get_unconfirmed_transactions(address):
          unconfirmed_deposits.append({
            'amount': deposit['amount'],
            'asset_name': asset.name,
            'confirmations': deposit['confirmations'],
            'required_confirmations': assets[asset.name].confirmations()
          })
      return render_template('dashboard/deposit.html', assets=coins, unconfirmed_deposits=unconfirmed_deposits)

  @get('/dashboard/withdraw')
  def withdraw(render_template, user):
    rate_limit(engine, ip=True)
    if not user: return redirect('/')
    with Session(engine) as session:
      coins = [asset.name for asset in session.query(Asset).all()]
      return render_template('dashboard/withdraw.html', assets=coins)

  @post('/dashboard/withdraw/<asset>')
  def withdraw(redirect, user, asset):
    rate_limit(engine, ip=True)
    if not user: return redirect('/')
    try:
      amount = Decimal(request.form['amount'])
    except:
      return redirect('/dashboard/withdraw', 'Please only use decimals for the amount.')
    result = exchange.withdraw(user.api_key, asset, request.form['address'], amount)
    if 'error' in result:
      return redirect('/dashboard/withdraw', result['error'])
    return redirect('/dashboard/withdraw', 'Successfully submitted the withdrawal request.')
