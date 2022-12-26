from flask import request, render_template, abort, make_response, redirect
from api import get_new_user_api_key
from entropy import random_128_bit_string

def pages(app, exchange):
  def check_user(f):
    def wrapper(csrf):
      if not exchange.check_user(request.cookies.get('api_key')):
        return redirect('/')
      return f(csrf)
    return wrapper

  def route(path):
    def decorator(f):
      @app.route(path, endpoint=random_128_bit_string(False))
      def wrapper():
        csrf = random_128_bit_string()
        response = make_response(f(f'<input type="hidden" name="csrf" value="{csrf}"/>'))
        response.set_cookie('csrf', csrf)
        return response
      return wrapper
    return decorator

  def post(path):
    def decorator(f):
      @app.post(path, endpoint=random_128_bit_string(False))
      def wrapper():
        if request.form['csrf'] != request.cookies.get('csrf'):
          abort(403)
        return f()
      return wrapper
    return decorator

  @route('/')
  def index(csrf):
    if 'api_key' in request.cookies:
      return redirect('/dashboard/balances')
    return render_template('index.html', invalid_login=request.args.get('invalid_login'), csrf=csrf)

  @post('/register')
  def register():
    api_key = get_new_user_api_key(exchange)
    if not api_key:
      abort(403)
    response = make_response(redirect('/dashboard/settings'))
    response.set_cookie('api_key', request.form['api_key'])
    return response

  @post('/login')
  def login():
    if exchange.check_user(request.form['api_key']):
      response = make_response(redirect('/dashboard/balances'))
      response.set_cookie('api_key', request.form['api_key'])
      return response
    return redirect('/?invalid_login=true')

  @post('/logout')
  def logout():
    response = make_response(redirect('/'))
    response.set_cookie('api_key', '', expires=0)
    return response

  @route('/dashboard/settings')
  @check_user
  def settings(csrf):
    return render_template('settings.html', markets=exchange.markets(), api_key=request.cookies['api_key'], csrf=csrf)

  @route('/dashboard/balances')
  @check_user
  def balances(csrf):
    return render_template('balances.html', markets=exchange.markets(), balances=exchange.balances(request.cookies['api_key']), csrf=csrf)

  @route('/dashboard/orders')
  @check_user
  def dashboard_orders(csrf):
    return render_template('orders.html', markets=exchange.markets(), orders=exchange.orders(request.cookies['api_key']), csrf=csrf)

  @route('/dashboard/trades')
  @check_user
  def dashboard_trades(csrf):
    return render_template('trades.html', markets=exchange.markets(), trades=exchange.trades(request.cookies['api_key']), csrf=csrf)

  @route('/api')
  def api(csrf):
    return render_template('api.html', api_key=request.cookies.get('api_key'), csrf=csrf)

  @route('/fees')
  def fees(csrf):
    return render_template('fees.html', api_key=request.cookies.get('api_key'), csrf=csrf)
