from flask import request, abort, make_response
from exchange import random_128_bit_string

def csrf(app, exchange):
  def get(path):
    def decorator(f):
      @app.route(path, endpoint=random_128_bit_string())
      def wrapper(*args, **kwargs):
        logged_in = exchange.check_user(request.cookies.get('api_key'))
        api_key = logged_in.api_key if logged_in else ''
        return f(f'<input type="hidden" name="csrf" value="{api_key}"/>', logged_in, *args, **kwargs)
      return wrapper
    return decorator

  def post(path):
    def decorator(f):
      @app.post(path, endpoint=random_128_bit_string())
      def wrapper(*args, **kwargs):
        logged_in = exchange.check_user(request.cookies.get('api_key'))
        if logged_in and request.form['csrf'] != logged_in.api_key:
          abort(403)
        api_key = logged_in.api_key if logged_in else ''
        return f(f'<input type="hidden" name="csrf" value="{api_key}"/>', logged_in, *args, **kwargs)
      return wrapper
    return decorator

  return get, post
