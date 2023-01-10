from flask import request, abort, render_template, redirect, make_response
from csrf import csrf
from db import User, LoginCode
from sqlalchemy.orm import Session
from exchange import random_128_bit_string
from mail import send_email
from rate_limit import rate_limit
from time import time
import re

def dashboard(app, exchange, engine):
  get, post = csrf(app, exchange)

  @get('/dashboard/new_user')
  def new_user(csrf, logged_in):
    rate_limit(engine, ip=True)
    if logged_in: return redirect('/dashboard/balances')
    return render_template('dashboard/new_user.html', csrf=csrf, logged_in=logged_in)

  @post('/dashboard/new_user')
  def new_user(csrf, logged_in):
    rate_limit(engine, ip=True)
    if logged_in: return redirect('/dashboard/balances')
    if not re.match('^[\w.-]+@[\w.-]+$', request.form['email']):
      return render_template('dashboard/new_user.html', error='Please enter a valid email address.', csrf=csrf, logged_in=logged_in)
    with Session(engine) as session:
      email_verification_code = random_128_bit_string()
      try:
        [user] = session.query(User).where(User.email == request.form['email'])
        return render_template('dashboard/new_user.html', error='A user with that email address already exists.', csrf=csrf, logged_in=logged_in)
      except:
        pass
      user = User(email=request.form['email'], api_key=random_128_bit_string(), email_verification_code=email_verification_code)
      session.add(user)
      session.commit()
    send_email(request.form['email'], "Welcome to Fryx Finance", render_template('emails/email_verification.html', email_verification_code=email_verification_code))
    return redirect('/dashboard/check_verification_email')

  @get('/dashboard/check_verification_email')
  def check_email(csrf, logged_in):
    rate_limit(engine, ip=True)
    if logged_in: return redirect('/dashboard/balances')
    return render_template('dashboard/check_verification_email.html', csrf=csrf, logged_in=logged_in)

  @get('/dashboard/verify_email/<code>')
  def verify_email(csrf, logged_in, code):
    rate_limit(engine, ip=True)
    with Session(engine) as session:
      try:
        [user] = session.query(User).where(User.email_verification_code == code)
      except:
        abort(404)
      user.email_verified = True
      user.email_verification_code = None
      session.commit()
      response = make_response(render_template('dashboard/verified_email.html', csrf=csrf, logged_in=True))
      response.set_cookie('api_key', user.api_key)
      return response

  @get('/dashboard/login')
  def login(csrf, logged_in):
    rate_limit(engine, ip=True)
    if logged_in: return redirect('/dashboard/balances')
    return render_template('dashboard/login.html', csrf=csrf, logged_in=logged_in)

  @post('/dashboard/login')
  def login(csrf, logged_in):
    rate_limit(engine, ip=True)
    if logged_in: return redirect('/dashboard/balances')
    with Session(engine) as session:
      try:
        [user] = session.query(User).where(User.email == request.form['email'])
      except:
        return render_template('dashboard/login.html', error='User not found.', csrf=csrf, logged_in=logged_in)
      if not user.email_verified:
        return render_template('dashboard/login.html', error='Please check your email for email verification before logging in.', csrf=csrf, logged_in=logged_in)
      login_code = LoginCode(user_id=user.id, code=random_128_bit_string(), expiry=int(time() + 60*60*2))
      session.add(login_code)
      session.commit()
      send_email(user.email, "Login to Fryx Finance", render_template('emails/login.html', code=login_code.code))
      return redirect('/dashboard/check_login_email')

  @get('/dashboard/check_login_email')
  def check_login_email(csrf, logged_in):
    rate_limit(engine, ip=True)
    if logged_in: return redirect('/dashboard/balances')
    return render_template('dashboard/check_login_email.html', csrf=csrf, logged_in=logged_in)

  @get('/dashboard/login/<code>')
  def login(csrf, logged_in, code):
    rate_limit(engine, ip=True)
    if logged_in: return redirect('/')
    with Session(engine) as session:
      try:
        [login_code] = session.query(LoginCode).where(LoginCode.code == code)
      except:
        abort(404)
      if login_code.expiry < time():
        return render_template('dashboard/login_code_expired.html', csrf=csrf, logged_in=logged_in)
      response = make_response(redirect('/dashboard/balances'))
      response.set_cookie('api_key', login_code.user.api_key)
      session.delete(login_code)
      session.commit()
      return response

  @post('/dashboard/logout')
  def logout(csrf, logged_in):
    rate_limit(engine, ip=True)
    if not logged_in: return redirect('/')
    response = make_response(redirect('/'))
    response.set_cookie('api_key', '', expires=0)
    return response

  @get('/dashboard/balances')
  def balances(csrf, logged_in):
    rate_limit(engine, ip=True)
    if not logged_in: return redirect('/')
    return render_template('dashboard/balances.html', balances=exchange.balances(logged_in.api_key), csrf=csrf, logged_in=logged_in)

  @get('/dashboard/orders/<market_name>')
  def orders(csrf, logged_in, market_name):
    rate_limit(engine, ip=True)
    if not logged_in: return redirect('/')
    market = exchange.check_market(market_name)
    if not market: abort(404)
    orders = exchange.orders(logged_in.api_key, market_name)
    return render_template('dashboard/orders.html', market=market, orders=orders, csrf=csrf, logged_in=logged_in)

  @post('/dashboard/orders/<market_name>')
  def orders(csrf, logged_in, market_name):
    rate_limit(engine, ip=True)
    if not logged_in: return redirect('/')
    market = exchange.check_market(market_name)
    if not market: abort(404)
    try:
      volume = Decimal(request.form['volume'])
      price = Decimal(request.form['price'])
    except:
      return render_template('dashboard/orders.html', message='Please enter only decimal values for volume and price.', market=market, orders=exchange.orders(logged_in.api_key, market_name), csrf=csrf, logged_in=logged_in)
    if request.form['type'] == 'buy':
      new_order = exchange.buy(logged_in.api_key, market_name, volume, price)
    else:
      new_order = exchange.sell(logged_in.api_key, market_name, volume, price)
    if 'error' in new_order:
      return render_template('dashboard/orders.html', message=new_order['error'], market=market, orders=exchange.orders(logged_in.api_key, market_name), csrf=csrf, logged_in=logged_in)
    if 'success' in new_order:
      return render_template('dashboard/orders.html', message='The order was filled.', market=market, orders=exchange.orders(logged_in.api_key, market_name), csrf=csrf, logged_in=logged_in)
    return render_template('dashboard/orders.html', message=f'A new order was created with order ID {new_order["order_id"]}.', market=market, orders=exchange.orders(logged_in.api_key, market_name), csrf=csrf, logged_in=logged_in)

  @get('/dashboard/trades/<market_name>')
  def trades(csrf, logged_in, market_name):
    rate_limit(engine, ip=True)
    if not logged_in: return redirect('/')
    market = exchange.check_market(market_name)
    if not market: abort(404)
    return render_template('dashboard/trades.html', market=market, trades=exchange.trades(logged_in.api_key, market_name), csrf=csrf, logged_in=logged_in)
